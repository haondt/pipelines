#!/usr/bin/env python3
"""
Example usage of the HaondtApp framework
"""

from app import HaondtApp

def main():
    # Create application
    app = HaondtApp("glance", namespace="glance")
    
    # Primary glance component
    glance_primary = (app.add_component("primary", "glanceapp/glance:v0.8.4")
        .with_port(8080)
        .with_ingress("glance.marble.local")
        .with_env({
            "PUID": "1000",
            "PGID": "1000",
            "TZ": "America/New_York"
        })
        .with_config_map("app-config", {
            "glance.yml": """
theme: dark
pages:
  - name: Home
    columns:
      - size: small
        widgets:
          - type: weather
            location: New York
""",
            "widgets.yml": "# Widget configuration here"
        })
        .with_secret("api-keys", {
            "weather_api_key": "your-api-key-here"
        })
        .with_resources(
            requests={"cpu": "50m", "memory": "64Mi"},
            limits={"cpu": "500m", "memory": "512Mi"}
        ))
    
    # Restic extension component
    restic = (app.add_component("restic", "restic-glance-extension:latest")
        .with_dependencies(["primary"])  # For future NetworkPolicy generation
        .with_env({
            "RESTIC_REPOSITORY": "s3:backup-bucket",
            "RESTIC_PASSWORD": "backup-password"
        })
        .with_secret("restic-creds", {
            "aws_access_key": "your-aws-key",
            "aws_secret_key": "your-aws-secret"
        }))
    
    # GitHub graph extension
    github = (app.add_component("github-graph", "glance-github-graph:0.0.2")
        .with_dependencies(["primary"])
        .with_env({
            "CACHE_TYPE": "memory",
            "CACHE_ENABLED": "true"
        })
        .with_config_map("github-config", {
            "repos.txt": "user/repo1\nuser/repo2\n"
        }))
    
    # Generate YAML output
    print("# Generated Kubernetes manifests:")
    print(app.to_yaml())
    
    print("\n" + "="*50)
    print("# Deployment commands:")
    print(f"# Deploy: python {__file__} | kubectl apply -f -")
    print(f"# Or use Helm state management:")
    print(f"# app.deploy_with_helm()")
    
    # Uncomment to actually deploy with Helm
    # result = app.deploy_with_helm(dry_run=True)
    # print(f"Helm dry-run result:\n{result}")

if __name__ == "__main__":
    main()