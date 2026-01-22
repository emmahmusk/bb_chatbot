class NormalizeTrailingSlashMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Remove a trailing slash from the path if it exists
        if request.path.endswith('/') and request.path != '/':
            request.path = request.path[:-1]

        response = self.get_response(request)
        return response