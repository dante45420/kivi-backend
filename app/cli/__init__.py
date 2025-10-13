def register_cli(app):
    from .admin import register_admin_commands
    register_admin_commands(app)
