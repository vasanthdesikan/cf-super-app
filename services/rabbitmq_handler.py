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
            
            # Use management API if available, otherwise try to get queue info
            # For basic pika, we'll try to get queues by declaring and checking
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
                # Fallback: return empty list if management API not available
                pass
            
            # If management API fails, return basic info
            return {
                'vhost': self.vhost,
                'queues': queues,
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

