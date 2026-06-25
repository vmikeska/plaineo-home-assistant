"""Lightweight test stubs for the Plaineo Home Assistant custom component."""

from __future__ import annotations

import sys
import types
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


if not hasattr(asyncio, "timeout"):
    @asynccontextmanager
    async def _timeout(_seconds):
        yield

    asyncio.timeout = _timeout


class _Schema:
    def __init__(self, schema):
        self.schema = schema

    def __call__(self, data):
        return data


voluptuous = types.ModuleType("voluptuous")
voluptuous.Schema = _Schema
sys.modules.setdefault("voluptuous", voluptuous)


class ClientError(Exception):
    pass


class ClientResponseError(ClientError):
    pass


class ClientSession:
    pass


class _WebResponse:
    def __init__(self, *, text: str = "", content_type: str = "text/plain"):
        self.text = text
        self.content_type = content_type


aiohttp = types.ModuleType("aiohttp")
aiohttp.ClientError = ClientError
aiohttp.ClientResponseError = ClientResponseError
aiohttp.ClientSession = ClientSession
aiohttp.web = types.SimpleNamespace(Response=_WebResponse, Request=object)
sys.modules.setdefault("aiohttp", aiohttp)
sys.modules.setdefault("aiohttp.web", aiohttp.web)


homeassistant = types.ModuleType("homeassistant")
sys.modules.setdefault("homeassistant", homeassistant)


class _FlowResultType:
    EXTERNAL_STEP = "external"
    EXTERNAL_STEP_DONE = "external_done"
    FORM = "form"
    CREATE_ENTRY = "create_entry"
    ABORT = "abort"


class ConfigFlow:
    source = "user"
    flow_id = "flow-123"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    async def async_set_unique_id(self, unique_id):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        self.abort_if_configured_called = True

    def async_external_step(self, *, step_id=None, url, description_placeholders=None):
        return {
            "type": _FlowResultType.EXTERNAL_STEP,
            "step_id": step_id,
            "url": url,
            "description_placeholders": description_placeholders,
        }

    def async_external_step_done(self, *, next_step_id):
        return {
            "type": _FlowResultType.EXTERNAL_STEP_DONE,
            "step_id": next_step_id,
        }

    def async_show_form(self, *, step_id, data_schema=None, description_placeholders=None, last_step=False):
        return {
            "type": _FlowResultType.FORM,
            "step_id": step_id,
            "data_schema": data_schema,
            "description_placeholders": description_placeholders,
            "last_step": last_step,
        }

    def async_create_entry(self, *, title, data):
        return {
            "type": _FlowResultType.CREATE_ENTRY,
            "title": title,
            "data": data,
        }

    def async_abort(self, *, reason):
        return {
            "type": _FlowResultType.ABORT,
            "reason": reason,
        }

    def async_update_reload_and_abort(self, entry, *, data):
        entry.data = data
        entry.reload_scheduled = True
        return self.async_abort(reason="reauth_successful")

    def _get_reauth_entry(self):
        return self.reauth_entry


config_entries = types.ModuleType("homeassistant.config_entries")
config_entries.ConfigEntry = object
config_entries.ConfigFlow = ConfigFlow
config_entries.ConfigFlowResult = dict
config_entries.FlowResultType = _FlowResultType
config_entries.SOURCE_REAUTH = "reauth"
sys.modules.setdefault("homeassistant.config_entries", config_entries)
homeassistant.config_entries = config_entries


class _Platform:
    CONVERSATION = "conversation"


const = types.ModuleType("homeassistant.const")
const.CONF_API_KEY = "api_key"
const.MATCH_ALL = "*"
const.Platform = _Platform
sys.modules.setdefault("homeassistant.const", const)


core = types.ModuleType("homeassistant.core")
core.HomeAssistant = object
sys.modules.setdefault("homeassistant.core", core)


helpers = types.ModuleType("homeassistant.helpers")
sys.modules.setdefault("homeassistant.helpers", helpers)


aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
aiohttp_client.async_get_clientsession = lambda hass: hass.session
sys.modules.setdefault("homeassistant.helpers.aiohttp_client", aiohttp_client)


network = types.ModuleType("homeassistant.helpers.network")
network.get_url = lambda hass, prefer_external=True: hass.base_url
sys.modules.setdefault("homeassistant.helpers.network", network)


class IntentResponse:
    def __init__(self, *, language):
        self.language = language
        self.speech = None

    def async_set_speech(self, speech):
        self.speech = speech


intent = types.ModuleType("homeassistant.helpers.intent")
intent.IntentResponse = IntentResponse
sys.modules.setdefault("homeassistant.helpers.intent", intent)
helpers.intent = intent


entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
entity_platform.AddConfigEntryEntitiesCallback = object
sys.modules.setdefault("homeassistant.helpers.entity_platform", entity_platform)


components = types.ModuleType("homeassistant.components")
sys.modules.setdefault("homeassistant.components", components)


class HomeAssistantView:
    pass


http = types.ModuleType("homeassistant.components.http")
http.HomeAssistantView = HomeAssistantView
sys.modules.setdefault("homeassistant.components.http", http)


class ConversationEntity:
    async def async_added_to_hass(self):
        return None

    async def async_will_remove_from_hass(self):
        return None


class AbstractConversationAgent:
    pass


class AssistantContent:
    def __init__(self, *, agent_id, content):
        self.agent_id = agent_id
        self.content = content


class ConversationResult:
    def __init__(self, *, response, conversation_id, continue_conversation):
        self.response = response
        self.conversation_id = conversation_id
        self.continue_conversation = continue_conversation


conversation = types.ModuleType("homeassistant.components.conversation")
conversation.ConversationEntity = ConversationEntity
conversation.AbstractConversationAgent = AbstractConversationAgent
conversation.AssistantContent = AssistantContent
conversation.ConversationResult = ConversationResult
conversation.ConversationInput = object
conversation.ChatLog = object
conversation.async_set_agent = lambda hass, config_entry, agent: None
conversation.async_unset_agent = lambda hass, config_entry: None
sys.modules.setdefault("homeassistant.components.conversation", conversation)
components.conversation = conversation
