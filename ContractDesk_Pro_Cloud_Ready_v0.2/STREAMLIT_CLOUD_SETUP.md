# Deploy ContractDesk Pro v0.2 to Streamlit Community Cloud

This is a **fictional portfolio demo**, not a secure contract-processing service or legal advice.

1. Create a new public repository on https://github.com/new (suggested name: `contractdesk-pro`).
2. Extract this ZIP. Open `ContractDesk_Pro_Cloud_Ready_v0.2` and upload the **contents** (not the ZIP and not its enclosing folder) to the GitHub repository using **Add file > Upload files**. The repository root must contain `app.py`, `requirements.txt`, `sample_playbook.json`, `sample_contracts/`, etc.
3. Go to https://share.streamlit.io, sign in with GitHub, select **Create app**, then **Yup, I have an app**.
4. Select your repository, branch `main` (if that is your default), and main file path `app.py`.
5. Optionally choose a readable app URL, and select **Deploy**.
6. Open the generated `https://...streamlit.app` link, click **Load fictional demonstration portfolio**, and test the workbench.

Important: This distribution intentionally omits `.streamlit/config.toml`, because the local package has `server.address = "127.0.0.1"`, which can prevent access on cloud hosting. Streamlit Community Cloud uses its own server settings.

Do not upload real contracts, secrets, API keys, organization playbooks, or protected data to this publicly accessible demo. It has no user authentication or persistent database. The offline mode works without API access. Ollama local mode will not connect to your laptop from the cloud. External AI features only work with a separately authorized API key, and the app has no controls to prevent public users from incurring charges if you expose a shared key. This is not recommended on a public demo.

Official docs: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
