"""RabbitMQ Service Handler"""

import os
import json
import pika
from datetime import datetime
from urllib.parse import urlparse
from .credential_helper import find_service_credentials, get_connection_params_from_creds

class RabbitMQHandler:
    """Handler for RabbitMQ transactions"""
    
    def __init__(self):
        """Initialize RabbitMQ connection"""
        # Service types to search for (Tanzu Data Services and standard)
        service_types = [
            'p.rabbitmq',      # Tanzu Data Services
            'p-rabbitmq',      # Standard Cloud Foundry
            'p.rabbitmq-for-kubernetes',
            'rabbitmq',
            'p.rabbitmq-for-kubernetes'
        ]
        
        # Try to find credentials from VCAP_SERVICES (supports Tanzu and UPS)
        creds = find_service_credentials(service_types)
        
        if creds:
            # Check if URI is available (common in Tanzu services)
            uri = creds.get('uri') or creds.get('url') or creds.get('amqp_uri')
            if uri:
                parsed = urlparse(uri)
                self.host = parsed.hostname or 'localhost'
                self.port = parsed.port or 5672
                self.username = parsed.username or 'guest'
                self.password = parsed.password or 'guest'
                self.vhost = parsed.path.lstrip('/') if parsed.path else '/'
            else:
                # Extract from credential dictionary
                params = get_connection_params_from_creds(creds, 'localhost', 5672)
                self.host = params['host']
                self.port = params['port'] or 5672
                self.username = params['username'] or 'guest'
                self.password = params['password'] or 'guest'
                self.vhost = params['vhost'] or '/'
        else:
            # Fallback to environment variables
            self.host = os.environ.get('RABBITMQ_HOST', 'localhost')
            self.port = int(os.environ.get('RABBITMQ_PORT', 5672))
            self.username = os.environ.get('RABBITMQ_USER', 'guest')
            self.password = os.environ.get('RABBITMQ_PASS', 'guest')
            self.vhost = os.environ.get('RABBITMQ_VHOST', '/')
        
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

