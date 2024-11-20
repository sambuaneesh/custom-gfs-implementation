clean:
	rm -rf data
	rm -rf logs
	rm -rf src/__pycache__

master:
	python run_master.py

chunk:
	python run_chunk_server.py --id $(word 2,$(MAKECMDGOALS))

client:
	streamlit run interfaces/streamlit_app.py --server.maxUploadSize 10000