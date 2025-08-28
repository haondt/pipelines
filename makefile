build-dockers:
	docker build -t docker-deployer:local ./images/docker-deployer

clean:
	docker rmi docker-deployer:local || true

