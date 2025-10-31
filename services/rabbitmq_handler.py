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

