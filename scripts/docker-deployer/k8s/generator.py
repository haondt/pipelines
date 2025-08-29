#!/usr/bin/env python3
"""
Haondt K8s Generator - Converts haondt.yml config to Kubernetes manifests
"""

import yaml
import os
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from kubernetes import client

class HaondtK8sGenerator:
    def __init__(self, app_dir: str):
        self.app_dir = Path(app_dir)
        self.app_name = self.app_dir.name
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load kubernetes.haondt.yml configuration"""
        config_file = self.app_dir / "kubernetes.haondt.yml"
        if not config_file.exists():
            raise FileNotFoundError(f"No kubernetes.haondt.yml found in {self.app_dir}")
            
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_env_vars(self) -> Dict[str, str]:
        """Load environment variables from env.haondt.yml"""
        env_file = self.app_dir / "env.haondt.yml"
        if env_file.exists():
            with open(env_file, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def generate_manifests(self) -> List[Dict[str, Any]]:
        """Generate all K8s manifests from haondt config"""
        manifests = []
        
        # Get app metadata
        app_name = self.config.get('metadata', {}).get('name', self.app_name)
        namespace = self.config.get('metadata', {}).get('namespace', self.app_name)
        
        # Create namespace if not default
        if namespace != "default":
            ns_manifest = self._create_namespace(namespace, app_name)
            manifests.append(ns_manifest)
        
        # Process each component
        components = self.config.get('spec', {}).get('components', {})
        for component_name, component_config in components.items():
            component_manifests = self._generate_component_manifests(
                app_name, namespace, component_name, component_config
            )
            manifests.extend(component_manifests)
            
        return manifests
    
    def _create_namespace(self, namespace: str, app_name: str) -> Dict[str, Any]:
        """Create namespace manifest"""
        ns = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace,
                labels={
                    "app.kubernetes.io/name": app_name,
                    "app.kubernetes.io/managed-by": "haondt-deployer"
                }
            )
        )
        return client.ApiClient().sanitize_for_serialization(ns)
    
    def _generate_component_manifests(self, app_name: str, namespace: str, 
                                    component_name: str, component_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate manifests for a single component"""
        manifests = []
        spec = component_config.get('spec', {})
        
        # Generate ConfigMaps for volumes
        config_maps = self._generate_config_maps(app_name, namespace, component_name, spec)
        manifests.extend(config_maps)
        
        # Generate Secrets for volumes  
        secrets = self._generate_secrets(app_name, namespace, component_name, spec)
        manifests.extend(secrets)
        
        # Generate Deployment
        deployment = self._generate_deployment(app_name, namespace, component_name, component_config)
        manifests.append(deployment)
        
        # Generate Service if networking.ingress is enabled
        networking = spec.get('networking', {})
        if networking.get('ingress', {}).get('enabled', False):
            service = self._generate_service(app_name, namespace, component_name, networking)
            manifests.append(service)
            
            # Generate Ingress
            ingress = self._generate_ingress(app_name, namespace, component_name, networking)
            manifests.append(ingress)
            
        return manifests
    
    def _generate_config_maps(self, app_name: str, namespace: str, 
                            component_name: str, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate ConfigMaps from volume definitions"""
        config_maps = []
        volumes = spec.get('volumes', {})
        
        for volume_name, volume_config in volumes.items():
            if 'configMap' in volume_config:
                cm_data = {}
                source = volume_config['configMap'].get('source', {})
                
                if 'glob' in source:
                    # Load files matching glob pattern
                    glob_pattern = source['glob']
                    config_dir = self.app_dir / os.path.dirname(glob_pattern)
                    if config_dir.exists():
                        for file_path in config_dir.rglob(os.path.basename(glob_pattern)):
                            if file_path.is_file():
                                with open(file_path, 'r') as f:
                                    cm_data[file_path.name] = f.read()
                elif isinstance(source, str):
                    # Inline content
                    cm_data['content'] = source
                elif 'path' in source:
                    # Single file
                    file_path = self.app_dir / source['path']
                    if file_path.exists():
                        with open(file_path, 'r') as f:
                            cm_data[file_path.name] = f.read()
                
                if cm_data:
                    cm = client.V1ConfigMap(
                        metadata=client.V1ObjectMeta(
                            name=f"{component_name}-{volume_name}",
                            namespace=namespace,
                            labels={
                                "app.kubernetes.io/name": app_name,
                                "app.kubernetes.io/component": component_name,
                                "app.kubernetes.io/managed-by": "haondt-deployer"
                            }
                        ),
                        data=cm_data
                    )
                    config_maps.append(client.ApiClient().sanitize_for_serialization(cm))
                    
        return config_maps
    
    def _generate_secrets(self, app_name: str, namespace: str, 
                         component_name: str, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate Secrets from volume definitions"""
        secrets = []
        volumes = spec.get('volumes', {})
        
        for volume_name, volume_config in volumes.items():
            if 'secret' in volume_config:
                secret_data = {}
                source = volume_config['secret'].get('source', {})
                
                if 'path' in source:
                    # Single file
                    file_path = self.app_dir / source['path']
                    if file_path.exists():
                        with open(file_path, 'r') as f:
                            secret_data[file_path.name] = f.read()
                elif isinstance(source, str):
                    # Inline content
                    secret_data['content'] = source
                
                if secret_data:
                    secret = client.V1Secret(
                        metadata=client.V1ObjectMeta(
                            name=f"{component_name}-{volume_name}",
                            namespace=namespace,
                            labels={
                                "app.kubernetes.io/name": app_name,
                                "app.kubernetes.io/component": component_name,
                                "app.kubernetes.io/managed-by": "haondt-deployer"
                            }
                        ),
                        string_data=secret_data
                    )
                    secrets.append(client.ApiClient().sanitize_for_serialization(secret))
                    
        return secrets
    
    def _generate_deployment(self, app_name: str, namespace: str, 
                           component_name: str, component_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Deployment manifest"""
        spec = component_config.get('spec', {})
        metadata = component_config.get('metadata', {})
        
        # Create container
        container = client.V1Container(
            name=component_name,
            image=spec['image'],
            resources=client.V1ResourceRequirements(
                requests=spec.get('resources', {}).get('requests', {"cpu": "10m", "memory": "16Mi"}),
                limits=spec.get('resources', {}).get('limits', {"cpu": "100m", "memory": "64Mi"})
            )
        )
        
        # Add ports if networking is configured
        networking = spec.get('networking', {})
        if networking.get('ingress', {}).get('enabled', False):
            port = networking['ingress'].get('port', 80)
            container.ports = [client.V1ContainerPort(container_port=port)]
        
        # Add environment variables (from env.haondt.yml or component spec)
        env_vars = self._load_env_vars()
        component_env = spec.get('environment', {})
        all_env = {**env_vars, **component_env}
        
        if all_env:
            container.env = [
                client.V1EnvVar(name=k, value=str(v)) 
                for k, v in all_env.items()
            ]
        
        # Add volume mounts
        volume_mounts = []
        volumes = []
        
        for volume_name, volume_config in spec.get('volumes', {}).items():
            mount_path = volume_config.get('path', f'/data/{volume_name}')
            volume_mounts.append(
                client.V1VolumeMount(name=volume_name, mount_path=mount_path)
            )
            
            # Create volume source
            if 'configMap' in volume_config:
                volumes.append(
                    client.V1Volume(
                        name=volume_name,
                        config_map=client.V1ConfigMapVolumeSource(
                            name=f"{component_name}-{volume_name}"
                        )
                    )
                )
            elif 'secret' in volume_config:
                volumes.append(
                    client.V1Volume(
                        name=volume_name,
                        secret=client.V1SecretVolumeSource(
                            secret_name=f"{component_name}-{volume_name}"
                        )
                    )
                )
        
        if volume_mounts:
            container.volume_mounts = volume_mounts
        
        # Create deployment
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=component_name,
                namespace=namespace,
                labels={
                    "app.kubernetes.io/name": app_name,
                    "app.kubernetes.io/component": component_name,
                    "app.kubernetes.io/managed-by": "haondt-deployer",
                    **metadata.get('labels', {})
                },
                annotations=metadata.get('annotations', {})
            ),
            spec=client.V1DeploymentSpec(
                replicas=spec.get('replicas', 1),
                selector=client.V1LabelSelector(
                    match_labels={
                        "app.kubernetes.io/name": app_name,
                        "app.kubernetes.io/component": component_name
                    }
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={
                            "app.kubernetes.io/name": app_name,
                            "app.kubernetes.io/component": component_name,
                            "app.kubernetes.io/managed-by": "haondt-deployer"
                        }
                    ),
                    spec=client.V1PodSpec(
                        containers=[container],
                        volumes=volumes if volumes else None
                    )
                )
            )
        )
        
        return client.ApiClient().sanitize_for_serialization(deployment)
    
    def _generate_service(self, app_name: str, namespace: str, 
                         component_name: str, networking: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Service manifest"""
        ingress_config = networking['ingress']
        port = ingress_config.get('port', 80)
        
        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=component_name,
                namespace=namespace,
                labels={
                    "app.kubernetes.io/name": app_name,
                    "app.kubernetes.io/component": component_name,
                    "app.kubernetes.io/managed-by": "haondt-deployer"
                }
            ),
            spec=client.V1ServiceSpec(
                selector={
                    "app.kubernetes.io/name": app_name,
                    "app.kubernetes.io/component": component_name
                },
                ports=[
                    client.V1ServicePort(port=80, target_port=port)
                ]
            )
        )
        
        return client.ApiClient().sanitize_for_serialization(service)
    
    def _generate_ingress(self, app_name: str, namespace: str, 
                         component_name: str, networking: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Ingress manifest"""
        ingress_config = networking['ingress']
        host = ingress_config['host']
        tls_enabled = ingress_config.get('tls', {}).get('enabled', True)
        
        ingress = client.V1Ingress(
            metadata=client.V1ObjectMeta(
                name=component_name,
                namespace=namespace,
                labels={
                    "app.kubernetes.io/name": app_name,
                    "app.kubernetes.io/component": component_name,
                    "app.kubernetes.io/managed-by": "haondt-deployer"
                },
                annotations={
                    "nginx.ingress.kubernetes.io/ssl-redirect": "true",
                    "cert-manager.io/cluster-issuer": "letsencrypt-prod"
                }
            ),
            spec=client.V1IngressSpec(
                ingress_class_name="nginx",
                rules=[
                    client.V1IngressRule(
                        host=host,
                        http=client.V1HTTPIngressRuleValue(
                            paths=[
                                client.V1HTTPIngressPath(
                                    path="/",
                                    path_type="Prefix",
                                    backend=client.V1IngressBackend(
                                        service=client.V1IngressServiceBackend(
                                            name=component_name,
                                            port=client.V1ServiceBackendPort(number=80)
                                        )
                                    )
                                )
                            ]
                        )
                    )
                ]
            )
        )
        
        if tls_enabled:
            ingress.spec.tls = [
                client.V1IngressTLS(
                    hosts=[host],
                    secret_name=f"{component_name}-tls"
                )
            ]
        
        return client.ApiClient().sanitize_for_serialization(ingress)
    
    def to_yaml(self) -> str:
        """Generate all manifests as YAML"""
        manifests = self.generate_manifests()
        yaml_parts = []
        for manifest in manifests:
            yaml_parts.append(yaml.dump(manifest, default_flow_style=False))
        return '---\n'.join(yaml_parts)
    
    def deploy_with_helm(self, release_name: Optional[str] = None, 
                        dry_run: bool = False, upgrade: bool = True) -> str:
        """Deploy using Helm for state management"""
        release_name = release_name or self.app_name
        namespace = self.config.get('metadata', {}).get('namespace', self.app_name)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            chart_dir = Path(temp_dir) / f"{self.app_name}-chart"
            chart_dir.mkdir()
            
            # Create Chart.yaml
            chart_yaml = {
                "apiVersion": "v2",
                "name": self.app_name,
                "description": f"Generated chart for {self.app_name}",
                "type": "application",
                "version": "0.1.0",
                "appVersion": "1.0.0"
            }
            
            with open(chart_dir / "Chart.yaml", 'w') as f:
                yaml.dump(chart_yaml, f)
            
            # Create empty values.yaml
            with open(chart_dir / "values.yaml", 'w') as f:
                f.write("# Generated chart - configuration comes from haondt files\n")
            
            # Create templates directory and add generated manifests
            templates_dir = chart_dir / "templates"
            templates_dir.mkdir()
            
            with open(templates_dir / "generated.yaml", 'w') as f:
                f.write(self.to_yaml())
            
            # Run helm install/upgrade
            cmd = [
                "helm",
                "upgrade" if upgrade else "install",
                release_name,
                str(chart_dir),
                "--namespace", namespace,
                "--create-namespace"
            ]
            
            if dry_run:
                cmd.extend(["--dry-run", "--debug"])
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return result.stdout
            except subprocess.CalledProcessError as e:
                raise Exception(f"Helm deployment failed: {e.stderr}")

def main():
    import sys
    if len(sys.argv) != 2:
        print("Usage: python generator.py <app_directory>")
        sys.exit(1)
    
    app_dir = sys.argv[1]
    generator = HaondtK8sGenerator(app_dir)
    
    # Generate and print YAML
    print(generator.to_yaml())

if __name__ == "__main__":
    main()