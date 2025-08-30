build-dockers:
	docker build -t docker-deployer:local ./images/docker-deployer
	docker build -t hephaestus:local ./images/hephaestus

clean:
	docker rmi docker-deployer:local || true

