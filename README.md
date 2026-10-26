# Perplexia: Langflow + LFX + Streamlit

A small deployment demo: the browser talks to Streamlit, Streamlit calls an
authenticated LFX HTTP server, and LFX executes an exported Langflow JSON flow.
The Langflow editor is not installed or running in the deployment.

## Design brief

- Visual thesis: a quiet, warm workspace with green accents and clear typography.
- Content plan: product name, one sentence of context, question box, answer.
- Interaction thesis: an obvious submit action, a visible running state, then a
  readable answer. No ornamental motion.

## Run locally

Use Python 3.13. Install requirements, set `OPENAI_API_KEY` in your environment,
then run:

```sh
streamlit run streamlit_app.py
```

Alternatively, copy `.streamlit/secrets.toml.example` to
`.streamlit/secrets.toml` and fill in the key. Never commit that file.

## Deploy on Streamlit Community Cloud

1. Connect this GitHub repository and select `streamlit_app.py`.
2. Select Python 3.13 in Advanced settings.
3. Deploy, restrict app access, and add `OPENAI_API_KEY` in the app's Secrets.
4. Open the app, ask a question, and inspect the answer's Run details.

Both processes run on the same Community Cloud instance. Streamlit starts
`lfx serve flows/perplexia.json` on an ephemeral loopback-only port, generates an
internal API token, and calls it over HTTP. No second hosting service is needed.
The LFX token is never sent to the browser.

## Flow

`flows/perplexia.json` is an importable Langflow 1.12 export with three stock
components: Chat Input → Language Model → Chat Output. It uses `gpt-6-luna` and
has no web search or persistent conversation history. Each question is independent.
The JSON embeds stock component source in the normal Langflow export format.

To change the behavior, import the flow into Langflow 1.12, edit and test it,
export it over `flows/perplexia.json`, then push the change. The app restarts LFX
when the flow content changes. Additional components may require additional
extension packages and credentials in the hosted environment.

MCP servers and databases are separate dependencies. Exporting a flow does not
deploy those services or copy Langflow's database. This first demo intentionally
uses a standalone flow so the deployment boundary is easy to see.
