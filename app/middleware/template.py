from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.utils.logger import logger


class TemplateMiddleware(BaseHTTPMiddleware):
    """
    Template middleware class
    
    This demonstrates how to create a middleware in FastAPI.
    """
    
    def __init__(self, app, some_config_value: str = "default"):
        """
        Initialize middleware with configuration
        
        Args:
            app: FastAPI application
            some_config_value: Example configuration parameter
        """
        super().__init__(app)
        self.some_config_value = some_config_value
        logger.info(f"TemplateMiddleware initialized with config: {some_config_value}")
        
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request, modify it or its response
        
        Args:
            request: FastAPI request
            call_next: Next middleware or endpoint in the chain
            
        Returns:
            Response: FastAPI response
        """
        # Pre-processing: before the request is handled by the endpoint
        logger.info("TemplateMiddleware pre-processing")
        
        # You can modify the request here
        # For example, add data to request.state
        request.state.example_data = "middleware_data"
        
        # Call the next middleware or endpoint
        try:
            response = await call_next(request)
            
            # Post-processing: after the request is handled by the endpoint
            logger.info("TemplateMiddleware post-processing")
            
            # You can modify the response here
            # For example, add custom headers
            response.headers["X-Template-Header"] = "middleware_response_header"
            
            return response
            
        except Exception as e:
            # Error handling: when an exception occurs during processing
            logger.error(f"TemplateMiddleware caught exception: {str(e)}", exc_info=True)
            
            # You can handle specific exceptions or rethrow them
            raise 