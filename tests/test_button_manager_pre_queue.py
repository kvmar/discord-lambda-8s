"""Tests for pre-queue button routing in ButtonManager."""

import pytest
from unittest.mock import MagicMock, patch
from core.ButtonManager import button_flow_tree, join_pre_queue_button, leave_pre_queue_button


class TestButtonFlowTreeRouting:
    """Tests for button_flow_tree pre-queue routing."""

    def test_route_join_pre_queue_button(self, mock_interaction):
        """button_flow_tree routes join_pre_queue custom_id correctly."""
        mock_interaction.custom_id = "join_pre_queue#main"

        with patch('core.ButtonManager.join_pre_queue_button') as mock_handler:
            button_flow_tree(mock_interaction)
            mock_handler.assert_called_once_with(mock_interaction.guild_id, mock_interaction)

    def test_route_leave_pre_queue_button(self, mock_interaction):
        """button_flow_tree routes leave_pre_queue custom_id correctly."""
        mock_interaction.custom_id = "leave_pre_queue#main"

        with patch('core.ButtonManager.leave_pre_queue_button') as mock_handler:
            button_flow_tree(mock_interaction)
            mock_handler.assert_called_once_with(mock_interaction.guild_id, mock_interaction)

    def test_pre_queue_routes_before_regular_queue(self, mock_interaction):
        """Pre-queue button checks happen before regular queue checks."""
        # This ensures substring matching doesn't cause collisions
        # (though "join_queue" is not in "join_pre_queue#main", we test the order is safe)
        mock_interaction.custom_id = "join_pre_queue#main"

        with patch('core.ButtonManager.join_pre_queue_button') as pre_handler, \
             patch('core.ButtonManager.join_queue_button') as queue_handler:
            button_flow_tree(mock_interaction)
            pre_handler.assert_called_once()
            queue_handler.assert_not_called()

    def test_other_buttons_still_route_correctly(self, mock_interaction):
        """Other buttons still route correctly (regression test)."""
        mock_interaction.custom_id = "join_queue#main"

        with patch('core.ButtonManager.join_queue_button') as mock_handler:
            button_flow_tree(mock_interaction)
            mock_handler.assert_called_once()


class TestJoinPreQueueButton:
    """Tests for join_pre_queue_button handler."""

    def test_join_pre_queue_button_calls_manager(self, mock_interaction, mock_queue_dao):
        """join_pre_queue_button delegates to QueueManager.add_pre_queue_player."""
        mock_interaction.custom_id = "join_pre_queue#main"
        embed = MagicMock()
        component = MagicMock()

        with patch('core.ButtonManager.QueueManager.add_pre_queue_player') as mock_add:
            mock_add.return_value = (embed, component)
            mock_queue_dao.get_queue = MagicMock()

            join_pre_queue_button("guild_123", mock_interaction)

            mock_add.assert_called_once_with(mock_interaction, "main")

    def test_join_pre_queue_button_extracts_queue_id(self, mock_interaction, mock_queue_dao):
        """join_pre_queue_button correctly extracts queue_id from custom_id."""
        mock_interaction.custom_id = "join_pre_queue#my_queue"
        embed = MagicMock()
        component = MagicMock()

        with patch('core.ButtonManager.QueueManager.add_pre_queue_player') as mock_add:
            mock_add.return_value = (embed, component)

            join_pre_queue_button("guild_123", mock_interaction)

            # Verify queue_id "my_queue" was extracted and passed
            call_args = mock_add.call_args[0]
            assert call_args[1] == "my_queue"

    def test_join_pre_queue_button_returns_none_on_failure(self, mock_interaction):
        """join_pre_queue_button returns early if add_pre_queue_player fails."""
        mock_interaction.custom_id = "join_pre_queue#main"

        with patch('core.ButtonManager.QueueManager.add_pre_queue_player') as mock_add:
            mock_add.return_value = None

            result = join_pre_queue_button("guild_123", mock_interaction)

            assert result is None

    def test_join_pre_queue_button_updates_queue_view(self, mock_interaction, mock_queue_dao):
        """join_pre_queue_button updates the queue view on success."""
        mock_interaction.custom_id = "join_pre_queue#main"
        embed = MagicMock()
        component = MagicMock()

        with patch('core.ButtonManager.QueueManager.add_pre_queue_player') as mock_add, \
             patch('core.ButtonManager.QueueManager.update_queue_view') as mock_update:
            mock_add.return_value = (embed, component)
            mock_queue_dao.get_queue = MagicMock()

            join_pre_queue_button("guild_123", mock_interaction)

            mock_update.assert_called_once()


class TestLeavePreQueueButton:
    """Tests for leave_pre_queue_button handler."""

    def test_leave_pre_queue_button_calls_manager(self, mock_interaction, mock_queue_dao):
        """leave_pre_queue_button delegates to QueueManager.remove_pre_queue_player."""
        mock_interaction.custom_id = "leave_pre_queue#main"
        embed = MagicMock()
        component = MagicMock()

        with patch('core.ButtonManager.QueueManager.remove_pre_queue_player') as mock_remove:
            mock_remove.return_value = (embed, component)
            mock_queue_dao.get_queue = MagicMock()

            leave_pre_queue_button("guild_123", mock_interaction)

            mock_remove.assert_called_once_with(mock_interaction, "main")

    def test_leave_pre_queue_button_extracts_queue_id(self, mock_interaction, mock_queue_dao):
        """leave_pre_queue_button correctly extracts queue_id from custom_id."""
        mock_interaction.custom_id = "leave_pre_queue#special_queue"
        embed = MagicMock()
        component = MagicMock()

        with patch('core.ButtonManager.QueueManager.remove_pre_queue_player') as mock_remove:
            mock_remove.return_value = (embed, component)

            leave_pre_queue_button("guild_123", mock_interaction)

            call_args = mock_remove.call_args[0]
            assert call_args[1] == "special_queue"

    def test_leave_pre_queue_button_returns_none_on_failure(self, mock_interaction):
        """leave_pre_queue_button returns early if remove_pre_queue_player fails."""
        mock_interaction.custom_id = "leave_pre_queue#main"

        with patch('core.ButtonManager.QueueManager.remove_pre_queue_player') as mock_remove:
            mock_remove.return_value = None

            result = leave_pre_queue_button("guild_123", mock_interaction)

            assert result is None

    def test_leave_pre_queue_button_updates_queue_view(self, mock_interaction, mock_queue_dao):
        """leave_pre_queue_button updates the queue view on success."""
        mock_interaction.custom_id = "leave_pre_queue#main"
        embed = MagicMock()
        component = MagicMock()

        with patch('core.ButtonManager.QueueManager.remove_pre_queue_player') as mock_remove, \
             patch('core.ButtonManager.QueueManager.update_queue_view') as mock_update:
            mock_remove.return_value = (embed, component)
            mock_queue_dao.get_queue = MagicMock()

            leave_pre_queue_button("guild_123", mock_interaction)

            mock_update.assert_called_once()


class TestButtonManagerIntegration:
    """Integration tests for button manager routing."""

    def test_join_then_leave_pre_queue_flow(self, mock_interaction, mock_queue_dao):
        """Player can join then leave pre-queue via buttons."""
        # First: join
        mock_interaction.custom_id = "join_pre_queue#main"
        with patch('core.ButtonManager.QueueManager.add_pre_queue_player') as mock_add:
            mock_add.return_value = (MagicMock(), MagicMock())
            join_pre_queue_button("guild_123", mock_interaction)
            mock_add.assert_called_once()

        # Then: leave
        mock_interaction.custom_id = "leave_pre_queue#main"
        with patch('core.ButtonManager.QueueManager.remove_pre_queue_player') as mock_remove:
            mock_remove.return_value = (MagicMock(), MagicMock())
            leave_pre_queue_button("guild_123", mock_interaction)
            mock_remove.assert_called_once()
