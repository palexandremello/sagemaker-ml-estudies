.PHONY: setup, enter_container, serve 

setup:
	docker compose down
	docker compose up -d --build

serve:
	docker exec sagemaker_endpoint poetry run serve

enter_train_container:
	docker exec -it train_model bash
