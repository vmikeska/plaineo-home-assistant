"""Conversation platform for Plaineo."""

from __future__ import annotations

from typing import Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import CannotConnect, InvalidAuth, PlaineoApiClient
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Plaineo conversation entity."""
    async_add_entities([PlaineoConversationEntity(hass, config_entry)])


class PlaineoConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
):
    """Plaineo conversation agent."""

    _attr_has_entity_name = True
    _attr_name = "Plaineo"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the Plaineo conversation entity."""
        self.hass = hass
        self.config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_conversation"

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """Register this entity as a conversation agent."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.config_entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister this entity as a conversation agent."""
        conversation.async_unset_agent(self.hass, self.config_entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Send the transcribed message to Plaineo and speak Plaineo's response."""
        client: PlaineoApiClient = self.hass.data[DOMAIN][self.config_entry.entry_id]

        try:
            result = await client.async_conversation(
                text=user_input.text,
                language=user_input.language,
                conversation_id=user_input.conversation_id,
                home_assistant_instance_id=getattr(self.hass.config, "uuid", None),
                device_id=user_input.device_id,
                satellite_id=user_input.satellite_id,
            )
            speech = result.speech
            continue_conversation = result.continue_conversation
            conversation_id = result.conversation_id or user_input.conversation_id
        except InvalidAuth:
            self.config_entry.async_start_reauth(self.hass)
            speech = "Plaineo rejected the configured API key."
            continue_conversation = False
            conversation_id = user_input.conversation_id
        except CannotConnect:
            speech = "I could not reach Plaineo right now."
            continue_conversation = False
            conversation_id = user_input.conversation_id

        chat_log.async_add_assistant_content_without_tools(
            conversation.AssistantContent(
                agent_id=user_input.agent_id,
                content=speech,
            )
        )

        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(speech)
        return conversation.ConversationResult(
            response=response,
            conversation_id=conversation_id,
            continue_conversation=continue_conversation,
        )
