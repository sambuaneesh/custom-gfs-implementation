clean:
	rm -rf data
	rm -rf logs
	rm -rf src/__pycache__

master:
	python run_master.py

chunk:
	$(eval ID := $(filter-out $@,$(MAKECMDGOALS)))
	@if [ "$(ID)" != "" ]; then \
		python run_chunk_server.py --id $(ID); \
	else \
		python run_chunk_server.py; \
	fi

client:
	streamlit run interfaces/streamlit_app.py --server.maxUploadSize 10000