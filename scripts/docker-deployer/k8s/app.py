from typing import Dict, List, Optional, Any
from kubernetes import client
import yaml
import os
import tempfile
import subprocess
from pathlib import Path

class HaondtApp:
    """Main application class for generating K8s manifests"""
    
    def __init__(self, name: str, namespace: str = "default"):
        self.name = name
        self.namespace = namespace
        self.manifests: List[Any] = []
        self.components: Dict[str, 'Component'] = {}
        
    def add_component(self, name: str, image: str) -> 'Component':
        """Add a component (deployment + service + configmaps etc)"""
        component = Component(self, name, image)
        self.components[name] = component
        return component
    
    def synthesize(self) -> List[Dict[str, Any]]:
        """Generate all K8s manifests as dictionaries"""
        all_manifests = []
        
        # Add namespace if not default
        if self.namespace != "default":
            namespace = client.V1Namespace(
                metadata=client.V1ObjectMeta(
                    name=self.namespace,
                    labels={
                        "app.kubernetes.io/name": self.name,
                        "app.kubernetes.io/managed-by": "haondt-deployer"
                    }
                )
            )
            all_manifests.append(client.ApiClient().sanitize_for_serialization(namespace))
        
        # Generate manifests for each component
        for component in self.components.values():
            all_manifests.extend(component.synthesize())
            
        # Add any custom manifests
        for manifest in self.manifests:
            if hasattr(manifest, 'to_dict'):
                all_manifests.append(manifest.to_dict())
            else:
                all_manifests.append(client.ApiClient().sanitize_for_serialization(manifest))
                
        return all_manifests
    
    def to_yaml(self) -> str:
        """Generate all manifests as YAML string"""
        manifests = self.synthesize()
        yaml_parts = []
        for manifest in manifests:
            yaml_parts.append(yaml.dump(manifest, default_flow_style=False))
        return '---\n'.join(yaml_parts)
    
    def deploy_with_helm(self, release_name: Optional[str] = None, 
                        dry_run: bool = False, upgrade: bool = True) -> str:
        """Deploy using Helm for state management"""
        release_name = release_name or self.name
        
        # Create temporary directory for Helm chart
        with tempfile.TemporaryDirectory() as temp_dir:
            chart_dir = Path(temp_dir) / f"{self.name}-chart"
            chart_dir.mkdir()
            
            # Create Chart.yaml
            chart_yaml = {
                "apiVersion": "v2",
                "name": self.name,
                "description": f"Generated chart for {self.name}",
                "type": "application", 
                "version": "0.1.0",
                "appVersion": "1.0.0"
            }
            
            with open(chart_dir / "Chart.yaml", 'w') as f:
                yaml.dump(chart_yaml, f)
            
            # Create empty values.yaml
            with open(chart_dir / "values.yaml", 'w') as f:
                f.write("# Generated chart - no values needed\n")
            
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
                "--namespace", self.namespace,
                "--create-namespace"
            ]
            
            if dry_run:
                cmd.extend(["--dry-run", "--debug"])
                
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return result.stdout
            except subprocess.CalledProcessError as e:
                raise Exception(f"Helm deployment failed: {e.stderr}")

class Component:
    """Represents a single component (deployment, service, configmaps, etc)"""
    
    def __init__(self, app: HaondtApp, name: str, image: str):
        self.app = app
        self.name = name
        self.image = image
        self.container_port: Optional[int] = None
        self.service_port: int = 80
        self.replicas: int = 1
        self.env_vars: Dict[str, str] = {}
        self.config_maps: Dict[str, Dict[str, str]] = {}
        self.secrets: Dict[str, Dict[str, str]] = {}
        self.dependencies: List[str] = []
        self.ingress_host: Optional[str] = None
        self.resource_requests = {"cpu": "10m", "memory": "16Mi"}
        self.resource_limits = {"cpu": "100m", "memory": "64Mi"}
        
    def with_port(self, port: int, service_port: Optional[int] = None) -> 'Component':
        """Set container port and optional service port"""
        self.container_port = port
        if service_port:
            self.service_port = service_port
        return self
    
    def with_env(self, env_vars: Dict[str, str]) -> 'Component':
        """Add environment variables"""
        self.env_vars.update(env_vars)
        return self
    
    def with_config_map(self, name: str, data: Dict[str, str]) -> 'Component':
        """Add a ConfigMap"""
        self.config_maps[name] = data
        return self
    
    def with_secret(self, name: str, data: Dict[str, str]) -> 'Component':
        """Add a Secret"""
        self.secrets[name] = data
        return self
    
    def with_dependencies(self, deps: List[str]) -> 'Component':
        """Add network dependencies (for future NetworkPolicy generation)"""
        self.dependencies.extend(deps)
        return self
    
    def with_ingress(self, host: str) -> 'Component':
        """Enable ingress for this component"""
        self.ingress_host = host
        return self
    
    def with_replicas(self, count: int) -> 'Component':
        """Set replica count"""
        self.replicas = count
        return self
    
    def with_resources(self, requests: Dict[str, str], limits: Dict[str, str]) -> 'Component':
        """Set resource requests and limits"""
        self.resource_requests = requests
        self.resource_limits = limits
        return self
    
    def synthesize(self) -> List[Dict[str, Any]]:
        """Generate all K8s manifests for this component"""
        manifests = []
        
        # Generate ConfigMaps
        for cm_name, cm_data in self.config_maps.items():
            config_map = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(
                    name=f"{self.name}-{cm_name}",
                    namespace=self.app.namespace,
                    labels={
                        "app.kubernetes.io/name": self.app.name,
                        "app.kubernetes.io/component": self.name,
                        "app.kubernetes.io/managed-by": "haondt-deployer"
                    }
                ),
                data=cm_data
            )
            manifests.append(client.ApiClient().sanitize_for_serialization(config_map))
        
        # Generate Secrets
        for secret_name, secret_data in self.secrets.items():
            secret = client.V1Secret(
                metadata=client.V1ObjectMeta(
                    name=f"{self.name}-{secret_name}",
                    namespace=self.app.namespace,
                    labels={
                        "app.kubernetes.io/name": self.app.name,
                        "app.kubernetes.io/component": self.name,
                        "app.kubernetes.io/managed-by": "haondt-deployer"
                    }
                ),
                string_data=secret_data
            )
            manifests.append(client.ApiClient().sanitize_for_serialization(secret))
        
        # Generate Deployment
        container = client.V1Container(
            name=self.name,
            image=self.image,
            resources=client.V1ResourceRequirements(
                requests=self.resource_requests,
                limits=self.resource_limits
            )
        )
        
        # Add port if specified
        if self.container_port:
            container.ports = [
                client.V1ContainerPort(container_port=self.container_port)
            ]
        
        # Add environment variables
        if self.env_vars:
            container.env = [
                client.V1EnvVar(name=k, value=v) 
                for k, v in self.env_vars.items()
            ]
        
        # Add volume mounts for ConfigMaps and Secrets
        volume_mounts = []
        volumes = []
        
        for cm_name in self.config_maps.keys():
            volume_name = f"{cm_name}-volume"
            volume_mounts.append(
                client.V1VolumeMount(
                    name=volume_name,
                    mount_path=f"/config/{cm_name}"
                )
            )
            volumes.append(
                client.V1Volume(
                    name=volume_name,
                    config_map=client.V1ConfigMapVolumeSource(
                        name=f"{self.name}-{cm_name}"
                    )
                )
            )
        
        for secret_name in self.secrets.keys():
            volume_name = f"{secret_name}-volume"
            volume_mounts.append(
                client.V1VolumeMount(
                    name=volume_name,
                    mount_path=f"/secrets/{secret_name}"
                )
            )
            volumes.append(
                client.V1Volume(
                    name=volume_name,
                    secret=client.V1SecretVolumeSource(
                        secret_name=f"{self.name}-{secret_name}"
                    )
                )
            )
        
        if volume_mounts:
            container.volume_mounts = volume_mounts
        
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=self.name,
                namespace=self.app.namespace,
                labels={
                    "app.kubernetes.io/name": self.app.name,
                    "app.kubernetes.io/component": self.name,
                    "app.kubernetes.io/managed-by": "haondt-deployer"
                }
            ),
            spec=client.V1DeploymentSpec(
                replicas=self.replicas,
                selector=client.V1LabelSelector(
                    match_labels={
                        "app.kubernetes.io/name": self.app.name,
                        "app.kubernetes.io/component": self.name
                    }
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={
                            "app.kubernetes.io/name": self.app.name,
                            "app.kubernetes.io/component": self.name,
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
        
        manifests.append(client.ApiClient().sanitize_for_serialization(deployment))
        
        # Generate Service if port is specified
        if self.container_port:
            service = client.V1Service(
                metadata=client.V1ObjectMeta(
                    name=self.name,
                    namespace=self.app.namespace,
                    labels={
                        "app.kubernetes.io/name": self.app.name,
                        "app.kubernetes.io/component": self.name,
                        "app.kubernetes.io/managed-by": "haondt-deployer"
                    }
                ),
                spec=client.V1ServiceSpec(
                    selector={
                        "app.kubernetes.io/name": self.app.name,
                        "app.kubernetes.io/component": self.name
                    },
                    ports=[
                        client.V1ServicePort(
                            port=self.service_port,
                            target_port=self.container_port
                        )
                    ]
                )
            )
            manifests.append(client.ApiClient().sanitize_for_serialization(service))
        
        # Generate Ingress if host is specified
        if self.ingress_host and self.container_port:
            ingress = client.V1Ingress(
                metadata=client.V1ObjectMeta(
                    name=self.name,
                    namespace=self.app.namespace,
                    labels={
                        "app.kubernetes.io/name": self.app.name,
                        "app.kubernetes.io/component": self.name,
                        "app.kubernetes.io/managed-by": "haondt-deployer"
                    },
                    annotations={
                        "nginx.ingress.kubernetes.io/ssl-redirect": "true",
                        "cert-manager.io/cluster-issuer": "letsencrypt-prod"
                    }
                ),
                spec=client.V1IngressSpec(
                    ingress_class_name="nginx",
                    tls=[
                        client.V1IngressTLS(
                            hosts=[self.ingress_host],
                            secret_name=f"{self.name}-tls"
                        )
                    ],
                    rules=[
                        client.V1IngressRule(
                            host=self.ingress_host,
                            http=client.V1HTTPIngressRuleValue(
                                paths=[
                                    client.V1HTTPIngressPath(
                                        path="/",
                                        path_type="Prefix",
                                        backend=client.V1IngressBackend(
                                            service=client.V1IngressServiceBackend(
                                                name=self.name,
                                                port=client.V1ServiceBackendPort(
                                                    number=self.service_port
                                                )
                                            )
                                        )
                                    )
                                ]
                            )
                        )
                    ]
                )
            )
            manifests.append(client.ApiClient().sanitize_for_serialization(ingress))
        
        return manifests