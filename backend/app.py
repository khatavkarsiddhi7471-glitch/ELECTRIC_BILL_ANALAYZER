"""
Main Flask application entry point for Smart Electricity Bill Analyzer.
Provides REST APIs and serves frontend static HTML/CSS/JS files.
"""

import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from backend.config import Config
from backend.utils.db import get_db

# Import route blueprints
from backend.routes.auth import auth_bp
from backend.routes.tariffs import tariffs_bp
from backend.routes.bills import bills_bp
from backend.routes.analytics import analytics_bp
from backend.routes.appliances import appliances_bp
from backend.routes.tips import tips_bp
from backend.routes.alerts import alerts_bp
from backend.routes.reports import reports_bp

def create_app(config_class=Config):
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    app.config.from_object(config_class)
    
    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize DB connection and default seeds
    get_db(config_class)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(tariffs_bp)
    app.register_blueprint(bills_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(appliances_bp)
    app.register_blueprint(tips_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(reports_bp)
    
    # Static frontend page routes
    @app.route("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/<path:path>")
    def serve_frontend_file(path):
        full_path = os.path.join(frontend_dir, path)
        if os.path.exists(full_path):
            return send_from_directory(frontend_dir, path)
        # If .html is omitted in the URL, try adding .html
        if os.path.exists(full_path + ".html"):
            return send_from_directory(frontend_dir, path + ".html")
        return send_from_directory(frontend_dir, "index.html")
        
    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Resource not found"}}), 404
        
    @app.errorhandler(500)
    def handle_500(e):
        return jsonify({"success": False, "error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected server error occurred"}}), 500

    return app

if __name__ == "__main__":
    application = create_app()
    port = int(os.getenv("PORT", 5000))
    print(f"\n=======================================================")
    print(f">> Smart Electricity Bill Analyzer Server Running")
    print(f">> Access Web UI at: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    application.run(host="127.0.0.1", port=port, debug=True)
