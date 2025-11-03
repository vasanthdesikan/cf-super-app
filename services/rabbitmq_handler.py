"""RabbitMQ Service Handler"""

import pika
from datetime import datetime
from .base_handler import MessageQueueHandler

class RabbitMQHandler(MessageQueueHandler):
    """Handler for RabbitMQ transactions"""
    
    def __init__(self):
        """Initialize RabbitMQ connection"""
        super().__init__(
            service_types=['p.rabbitmq', 'p-rabbitmq', 'rabbitmq'],
            default_port=5672,
            env_prefix='RABBITMQ'
        )
        self.connection = None
        self.channel = None
    
    def _get_connection(self):
        """Get or create RabbitMQ connection"""
        if self.connection is None or self.connection.is_closed:
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.vhost,
                credentials=credentials
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
        return self.connection, self.channel
    
    def test_transaction(self, data=None):
        """Test RabbitMQ transaction (publish and consume)"""
        if data is None:
            data = {}
        
        queue_name = data.get('queue_name', 'test_queue')
        message = data.get('message', f'Test message at {datetime.now().isoformat()}')
        
        try:
            conn, channel = self._get_connection()
            
            # Declare queue
            channel.queue_declare(queue=queue_name, durable=False)
            
            # Publish message
            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
            )
            
            # Consume message
            method_frame, header_frame, body = channel.basic_get(queue=queue_name, auto_ack=True)
            
            consumed_message = body.decode('utf-8') if body else None
            
            return {
                'action': 'publish_and_consume',
                'queue': queue_name,
                'published': message,
                'consumed': consumed_message,
                'status': 'success'
            }
        except Exception as e:
            raise Exception(f"RabbitMQ transaction failed: {str(e)}")
        finally:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.connection = None
                self.channel = None
    
    def list_queues(self):
        """List all queues"""
        try:
            conn, channel = self._get_connection()
            queues = []
            
            # Try to use management HTTP API if available
            try:
                import requests
                management_url = f"http://{self.host}:15672"
                auth = (self.username, self.password)
                
                # Try to get queues from management API
                response = requests.get(f"{management_url}/api/queues/{self.vhost}", 
                                       auth=auth, timeout=2)
                if response.status_code == 200:
                    queue_data = response.json()
                    for queue in queue_data:
                        queues.append({
                            'name': queue.get('name', ''),
                            'messages': queue.get('messages', 0),
                            'consumers': queue.get('consumers', 0),
                            'durable': queue.get('durable', False),
                            'auto_delete': queue.get('auto_delete', False)
                        })
                    return {
                        'vhost': self.vhost,
                        'queues': queues,
                        'count': len(queues)
                    }
            except:
                # Fallback: try AMQP method if management API not available
                pass
            
            # If no queues found via management API, try AMQP method
            if not queues:
                # Check test_queue (common queue name)
                # Try non-passive first to find or create the queue
                queue_name = 'test_queue'
                try:
                    # First try passive to see if queue exists
                    try:
                        result = channel.queue_declare(queue=queue_name, passive=True)
                    except Exception:
                        # Queue doesn't exist, try non-passive (will create if needed)
                        result = channel.queue_declare(queue=queue_name, durable=False)
                    
                    # If queue_declare succeeded, the queue exists (or was created)
                    message_count = 0
                    consumer_count = 0
                    if result:
                        if hasattr(result, 'method'):
                            message_count = getattr(result.method, 'message_count', 0)
                            consumer_count = getattr(result.method, 'consumer_count', 0)
                        # Also try direct attributes
                        elif hasattr(result, 'message_count'):
                            message_count = result.message_count
                        elif hasattr(result, 'consumer_count'):
                            consumer_count = result.consumer_count
                    
                    # Queue exists, add it to the list
                    # Peek at messages in the queue (up to 5 messages)
                    # Note: We'll consume and republish to peek at contents
                    queue_messages = []
                    if message_count > 0:
                        # Create a separate channel for peeking to avoid affecting the main channel
                        peek_channel = conn.channel()
                        try:
                            messages_to_republish = []
                            for _ in range(min(message_count, 5)):
                                method_frame, header_frame, body = peek_channel.basic_get(
                                    queue=queue_name, 
                                    auto_ack=False
                                )
                                if method_frame and body:
                                    try:
                                        message_content = body.decode('utf-8')
                                        queue_messages.append(message_content)
                                        # Store for republishing
                                        messages_to_republish.append({
                                            'body': body
                                        })
                                        # Acknowledge to remove from queue
                                        peek_channel.basic_ack(method_frame.delivery_tag)
                                    except Exception:
                                        queue_messages.append(f"<binary data: {len(body)} bytes>")
                                        messages_to_republish.append({
                                            'body': body
                                        })
                                        peek_channel.basic_ack(method_frame.delivery_tag)
                                else:
                                    break
                            
                            # Republish messages back to queue (to restore queue state)
                            for msg_data in messages_to_republish:
                                peek_channel.basic_publish(
                                    exchange='',
                                    routing_key=queue_name,
                                    body=msg_data['body'],
                                    properties=pika.BasicProperties(delivery_mode=1)
                                )
                            peek_channel.close()
                        except Exception as e:
                            # If peeking fails, just continue without messages
                            try:
                                peek_channel.close()
                            except:
                                pass
                    
                    # Always add queue if we got here (queue_declare succeeded)
                    queues.append({
                        'name': queue_name,
                        'messages': message_count,
                        'consumers': consumer_count,
                        'durable': False,
                        'auto_delete': False,
                        'message_contents': queue_messages  # Add message contents (empty list if no messages)
                    })
                except Exception as e:
                    # Queue operation failed, skip
                    pass
            
            if queues:
                return {
                    'vhost': self.vhost,
                    'queues': queues,
                    'count': len(queues),
                    'note': f'Found {len(queues)} queue(s) via AMQP.'
                }
            else:
                return {
                    'vhost': self.vhost,
                    'queues': [],
                    'count': 0,
                    'note': 'Management API not available. Queue listing requires RabbitMQ management plugin.'
                }
        except Exception as e:
            raise Exception(f"Failed to list RabbitMQ queues: {str(e)}")
        finally:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.connection = None
                self.channel = None
    
    def publish_message(self, queue_name, message, durable=False):
        """Publish a message to a queue (CREATE)"""
        try:
            conn, channel = self._get_connection()
            
            # Declare queue
            channel.queue_declare(queue=queue_name, durable=durable)
            
            # Publish message
            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2 if durable else 1
                )
            )
            
            return {
                'action': 'publish',
                'queue': queue_name,
                'message': message,
                'status': 'success'
            }
        except Exception as e:
            raise Exception(f"Failed to publish message: {str(e)}")
        finally:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.connection = None
                self.channel = None
    
    def consume_message(self, queue_name, auto_ack=True):
        """Consume a message from a queue (READ)"""
        try:
            conn, channel = self._get_connection()
            
            # Declare queue
            channel.queue_declare(queue=queue_name, durable=False)
            
            # Consume message
            method_frame, header_frame, body = channel.basic_get(queue=queue_name, auto_ack=auto_ack)
            
            if method_frame:
                message = body.decode('utf-8') if body else None
                return {
                    'action': 'consume',
                    'queue': queue_name,
                    'message': message,
                    'delivery_tag': method_frame.delivery_tag,
                    'redelivered': method_frame.redelivered,
                    'status': 'success'
                }
            else:
                return {
                    'action': 'consume',
                    'queue': queue_name,
                    'message': None,
                    'status': 'empty',
                    'note': 'No messages available in queue'
                }
        except Exception as e:
            raise Exception(f"Failed to consume message: {str(e)}")
        finally:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.connection = None
                self.channel = None
    
    def purge_queue(self, queue_name):
        """Purge all messages from a queue (DELETE)"""
        try:
            conn, channel = self._get_connection()
            
            # Declare queue
            channel.queue_declare(queue=queue_name, durable=False)
            
            # Purge queue
            purged_result = channel.queue_purge(queue=queue_name)
            
            # Extract message count from result
            messages_purged = 0
            if hasattr(purged_result, 'method') and hasattr(purged_result.method, 'message_count'):
                messages_purged = purged_result.method.message_count
            
            return {
                'action': 'purge',
                'queue': queue_name,
                'messages_purged': messages_purged,
                'status': 'success'
            }
        except Exception as e:
            raise Exception(f"Failed to purge queue: {str(e)}")
        finally:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.connection = None
                self.channel = None
    
    def delete_queue(self, queue_name, if_unused=False, if_empty=False):
        """Delete a queue completely"""
        try:
            conn, channel = self._get_connection()
            
            # Delete queue
            deleted_result = channel.queue_delete(
                queue=queue_name,
                if_unused=if_unused,
                if_empty=if_empty
            )
            
            # Extract message count from result
            messages_deleted = 0
            if hasattr(deleted_result, 'method') and hasattr(deleted_result.method, 'message_count'):
                messages_deleted = deleted_result.method.message_count
            
            return {
                'action': 'delete_queue',
                'queue': queue_name,
                'messages_deleted': messages_deleted,
                'status': 'success'
            }
        except Exception as e:
            raise Exception(f"Failed to delete queue: {str(e)}")
        finally:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                self.connection = None
                self.channel = None
