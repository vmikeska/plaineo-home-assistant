# Plaineo Home Assistant Integration

Use Home Assistant Voice and Nabu devices as a Plaineo voice entry point.

The integration is intentionally small:

```text
wake word -> Home Assistant STT -> Plaineo conversation agent -> Plaineo backend -> Home Assistant TTS
```

Home Assistant handles the voice transport. Plaineo handles the command logic.

## Installation With HACS

This repository can be installed as a HACS custom repository.

1. In Home Assistant, open **HACS**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add this repository URL:

   ```text
   https://github.com/vmikeska/plaineo-home-assistant
   ```

4. Select category **Integration**.
5. Install **Plaineo**.
6. Restart Home Assistant.

## Manual Installation

Copy `custom_components/plaineo` into your Home Assistant config directory:

```powershell
Copy-Item -Recurse -Force .\custom_components\plaineo C:\homeassistant\custom_components\
docker restart homeassistant
```

## Setup

1. In Home Assistant, go to **Settings -> Devices & services -> Add integration**.
2. Search for **Plaineo**.
3. Sign in through Plaineo when Home Assistant opens the authorization flow.
4. Open your **Home Assistant Voice** satellite device, usually under **ESPHome**.
5. Set the device **Assistant** or **Assist pipeline** to **Plaineo**.

Removing the Plaineo integration from Home Assistant revokes the Plaineo token. Restarting or unloading Home Assistant does not revoke it.

## Tests

Install the lightweight test dependencies and run the custom component tests:

```powershell
python -m pip install -r requirements-test.txt
python -m pytest tests
python -m py_compile custom_components\plaineo\__init__.py custom_components\plaineo\api.py custom_components\plaineo\auth.py custom_components\plaineo\config_flow.py custom_components\plaineo\conversation.py
```

## License

Apache-2.0
