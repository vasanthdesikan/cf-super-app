"""Custom Exceptions for Service Operations"""


class ServiceException(Exception):
    """Base exception for service operations"""
    pass


class ServiceNotFoundError(ServiceException):
    """Raised when service is not found or not enabled"""
    pass


class ServiceConnectionError(ServiceException):
    """Raised when service connection fails"""
    pass


class ServiceOperationError(ServiceException):
    """Raised when service operation fails"""
    pass

