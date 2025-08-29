import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from click.testing import CliRunner

from spotify_imessage.cli import (
    _validate_spotify_credentials,
    _validate_playlist_id,
    _validate_chat_name,
    _validate_template_name,
    _validate_backup_name,
    _validate_ids,
    _load_config,
    _save_config,
    _get_config_value,
    _load_templates,
    _save_templates,
    _create_template,
    _load_backups,
    _save_backups,
    _create_backup,
    _parse_date_from_line,
    _is_line_date,
    cli
)


class TestValidation:
    """Test validation functions."""
    
    def test_validate_spotify_credentials_valid(self):
        """Test valid Spotify credentials."""
        _validate_spotify_credentials("valid_id", "valid_secret")
        # Should not raise exception
    
    def test_validate_spotify_credentials_missing_id(self):
        """Test missing client ID."""
        with pytest.raises(Exception, match="Spotify Client ID is required"):
            _validate_spotify_credentials(None, "valid_secret")
    
    def test_validate_spotify_credentials_missing_secret(self):
        """Test missing client secret."""
        with pytest.raises(Exception, match="Spotify Client Secret is required"):
            _validate_spotify_credentials("valid_id", None)
    
    def test_validate_playlist_id_valid(self):
        """Test valid playlist ID."""
        _validate_playlist_id("1c68uZNKCUx7a1l6wr97D3")
        # Should not raise exception
    
    def test_validate_playlist_id_invalid(self):
        """Test invalid playlist ID."""
        with pytest.raises(Exception, match="Invalid playlist ID"):
            _validate_playlist_id("invalid")
    
    def test_validate_playlist_id_too_short(self):
        """Test playlist ID too short."""
        with pytest.raises(Exception, match="Invalid playlist ID"):
            _validate_playlist_id("123456789012345678901")
    
    def test_validate_playlist_id_too_long(self):
        """Test playlist ID too long."""
        with pytest.raises(Exception, match="Invalid playlist ID"):
            _validate_playlist_id("12345678901234567890123")
    
    def test_validate_chat_name_valid(self):
        """Test valid chat name."""
        _validate_chat_name("Valid Chat Name")
        # Should not raise exception
    
    def test_validate_chat_name_empty(self):
        """Test empty chat name."""
        with pytest.raises(Exception, match="Chat name cannot be empty"):
            _validate_chat_name("")
    
    def test_validate_chat_name_whitespace(self):
        """Test whitespace-only chat name."""
        with pytest.raises(Exception, match="Chat name cannot be empty"):
            _validate_chat_name("   ")
    
    def test_validate_template_name_valid(self):
        """Test valid template name."""
        _validate_template_name("Valid Template Name")
        _validate_template_name("valid-template-name")
        _validate_template_name("valid_template_name")
        # Should not raise exception
    
    def test_validate_template_name_empty(self):
        """Test empty template name."""
        with pytest.raises(Exception, match="Template name cannot be empty"):
            _validate_template_name("")
    
    def test_validate_template_name_too_long(self):
        """Test template name too long."""
        long_name = "a" * 51
        with pytest.raises(Exception, match="Template name must be 50 characters or less"):
            _validate_template_name(long_name)
    
    def test_validate_template_name_invalid_chars(self):
        """Test template name with invalid characters."""
        with pytest.raises(Exception, match="Template name can only contain letters, numbers, spaces, hyphens, and underscores"):
            _validate_template_name("Invalid@Name")
    
    def test_validate_backup_name_valid(self):
        """Test valid backup name."""
        _validate_backup_name("Valid Backup Name")
        _validate_backup_name("valid-backup-name")
        _validate_backup_name("valid_backup_name")
        # Should not raise exception
    
    def test_validate_backup_name_empty(self):
        """Test empty backup name."""
        with pytest.raises(Exception, match="Backup name cannot be empty"):
            _validate_backup_name("")
    
    def test_validate_backup_name_too_long(self):
        """Test backup name too long."""
        long_name = "a" * 51
        with pytest.raises(Exception, match="Backup name must be 50 characters or less"):
            _validate_backup_name(long_name)
    
    def test_validate_backup_name_invalid_chars(self):
        """Test backup name with invalid characters."""
        with pytest.raises(Exception, match="Backup name can only contain letters, numbers, spaces, hyphens, and underscores"):
            _validate_backup_name("Invalid@Name")
    
    def test_validate_ids_valid(self):
        """Test valid track IDs."""
        valid_ids = ["4iV5W9uYEdYUVa79Axb7Rh", "6rqhFgbbKwnb9MLmUQDhG6"]
        result = _validate_ids(valid_ids)
        assert result == valid_ids
    
    def test_validate_ids_invalid(self):
        """Test invalid track IDs."""
        mixed_ids = ["4iV5W9uYEdYUVa79Axb7Rh", "invalid", "6rqhFgbbKwnb9MLmUQDhG6"]
        result = _validate_ids(mixed_ids)
        assert result == ["4iV5W9uYEdYUVa79Axb7Rh", "6rqhFgbbKwnb9MLmUQDhG6"]
    
    def test_validate_ids_empty(self):
        """Test empty track IDs list."""
        result = _validate_ids([])
        assert result == []


class TestConfiguration:
    """Test configuration functions."""
    
    def test_load_config_nonexistent(self, tmp_path):
        """Test loading non-existent config file."""
        with patch('spotify_imessage.cli.DEFAULT_CONFIG_PATH', str(tmp_path / 'nonexistent.json')):
            config = _load_config()
            assert config == {}
    
    def test_load_config_valid(self, tmp_path):
        """Test loading valid config file."""
        config_data = {"test_key": "test_value"}
        config_file = tmp_path / 'config.json'
        config_file.write_text(json.dumps(config_data))
        
        with patch('spotify_imessage.cli.DEFAULT_CONFIG_PATH', str(config_file)):
            config = _load_config()
            assert config == config_data
    
    def test_load_config_invalid_json(self, tmp_path):
        """Test loading invalid JSON config file."""
        config_file = tmp_path / 'config.json'
        config_file.write_text("invalid json")
        
        with patch('spotify_imessage.cli.DEFAULT_CONFIG_PATH', str(config_file)):
            config = _load_config()
            assert config == {}
    
    def test_save_config(self, tmp_path):
        """Test saving config file."""
        config_data = {"test_key": "test_value"}
        config_file = tmp_path / 'config.json'
        
        with patch('spotify_imessage.cli.DEFAULT_CONFIG_PATH', str(config_file)):
            _save_config(config_data)
            assert config_file.exists()
            saved_data = json.loads(config_file.read_text())
            assert saved_data == config_data
    
    def test_get_config_value_found(self, tmp_path):
        """Test getting config value that exists."""
        config_data = {"test_key": "test_value"}
        config_file = tmp_path / 'config.json'
        config_file.write_text(json.dumps(config_data))
        
        with patch('spotify_imessage.cli.DEFAULT_CONFIG_PATH', str(config_file)):
            value = _get_config_value('test_key', 'default')
            assert value == 'test_value'
    
    def test_get_config_value_not_found(self, tmp_path):
        """Test getting config value that doesn't exist."""
        config_data = {"other_key": "other_value"}
        config_file = tmp_path / 'config.json'
        config_file.write_text(json.dumps(config_data))
        
        with patch('spotify_imessage.cli.DEFAULT_CONFIG_PATH', str(config_file)):
            value = _get_config_value('test_key', 'default')
            assert value == 'default'


class TestTemplates:
    """Test template functions."""
    
    def test_load_templates_empty(self, tmp_path):
        """Test loading empty templates."""
        config_data = {}
        config_file = tmp_path / 'config.json'
        config_file.write_text(json.dumps(config_data))
        
        with patch('spotify_imessage.cli.DEFAULT_CONFIG_PATH', str(config_file)):
            templates = _load_templates()
            assert templates == {}
    
    def test_load_templates_with_data(self, tmp_path):
        """Test loading templates with data."""
        config_data = {
            "templates": {
                "test_template": {
                    "name": "test_template",
                    "playlist_id": "test_playlist",
                    "description": "test description",
                    "tags": ["test"],
                    "created_at": "2025-01-01T00:00:00"
                }
            }
        }
        config_file = tmp_path / 'config.json'
        config_file.write_text(json.dumps(config_data))
        
        with patch('spotify_imessage.cli.DEFAULT_CONFIG_PATH', str(config_file)):
            templates = _load_templates()
            assert "test_template" in templates
            assert templates["test_template"]["name"] == "test_template"
    
    def test_save_templates(self, tmp_path):
        """Test saving templates."""
        templates_data = {
            "test_template": {
                "name": "test_template",
                "playlist_id": "test_playlist",
                "description": "test description",
                "tags": ["test"],
                "created_at": "2025-01-01T00:00:00"
            }
        }
        config_file = tmp_path / 'config.json'
        
        with patch('spotify_imessage.cli.DEFAULT_CONFIG_PATH', str(config_file)):
            _save_templates(templates_data)
            assert config_file.exists()
            saved_data = json.loads(config_file.read_text())
            assert "templates" in saved_data
            assert saved_data["templates"] == templates_data
    
    def test_create_template(self):
        """Test creating template."""
        template = _create_template(
            name="test_template",
            playlist_id="test_playlist",
            description="test description",
            tags=["test", "music"]
        )
        
        assert template["name"] == "test_template"
        assert template["playlist_id"] == "test_playlist"
        assert template["description"] == "test description"
        assert template["tags"] == ["test", "music"]
        assert "created_at" in template


class TestBackups:
    """Test backup functions."""
    
    def test_load_backups_empty(self, tmp_path):
        """Test loading empty backups."""
        config_data = {}
        config_file = tmp_path / 'config.json'
        config_file.write_text(json.dumps(config_data))
        
        with patch('spotify_imessage.cli.DEFAULT_CONFIG_PATH', str(config_file)):
            backups = _load_backups()
            assert backups == {}
    
    def test_load_backups_with_data(self, tmp_path):
        """Test loading backups with data."""
        config_data = {
            "backups": {
                "test_backup": {
                    "name": "test_backup",
                    "playlist_id": "test_playlist",
                    "tracks": [],
                    "description": "test description",
                    "created_at": "2025-01-01T00:00:00",
                    "track_count": 0
                }
            }
        }
        config_file = tmp_path / 'config.json'
        config_file.write_text(json.dumps(config_data))
        
        with patch('spotify_imessage.cli.DEFAULT_CONFIG_PATH', str(config_file)):
            backups = _load_backups()
            assert "test_backup" in backups
            assert backups["test_backup"]["name"] == "test_backup"
    
    def test_save_backups(self, tmp_path):
        """Test saving backups."""
        backups_data = {
            "test_backup": {
                "name": "test_backup",
                "playlist_id": "test_playlist",
                "tracks": [],
                "description": "test description",
                "created_at": "2025-01-01T00:00:00",
                "track_count": 0
            }
        }
        config_file = tmp_path / 'config.json'
        
        with patch('spotify_imessage.cli.DEFAULT_CONFIG_PATH', str(config_file)):
            _save_backups(backups_data)
            assert config_file.exists()
            saved_data = json.loads(config_file.read_text())
            assert "backups" in saved_data
            assert saved_data["backups"] == backups_data
    
    def test_create_backup(self):
        """Test creating backup."""
        tracks = [{"id": "track1", "name": "Test Track"}]
        backup = _create_backup(
            name="test_backup",
            playlist_id="test_playlist",
            tracks=tracks,
            description="test description"
        )
        
        assert backup["name"] == "test_backup"
        assert backup["playlist_id"] == "test_playlist"
        assert backup["tracks"] == tracks
        assert backup["description"] == "test description"
        assert backup["track_count"] == 1
        assert "created_at" in backup


class TestDateParsing:
    """Test date parsing functions."""
    
    def test_parse_date_from_line_valid(self):
        """Test parsing valid date line."""
        date_str = "Dec 01, 2022 5:10:27 PM"
        result = _parse_date_from_line(date_str)
        assert isinstance(result, datetime)
        assert result.year == 2022
        assert result.month == 12
        assert result.day == 1
    
    def test_parse_date_from_line_invalid(self):
        """Test parsing invalid date line."""
        with pytest.raises(ValueError):
            _parse_date_from_line("invalid date")
    
    def test_is_line_date_valid(self):
        """Test valid date line detection."""
        assert _is_line_date("Dec 01, 2022 5:10:27 PM") == True
        assert _is_line_date("December 01, 2022 5:10:27 PM") == True
        assert _is_line_date("Dec 01, 2022 17:10:27") == True
    
    def test_is_line_date_invalid(self):
        """Test invalid date line detection."""
        assert _is_line_date("") == False
        assert _is_line_date("This is not a date") == False
        assert _is_line_date("2022-12-01") == False


class TestCLICommands:
    """Test CLI commands."""
    
    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()
    
    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "Manage playlist templates" in result.output
        assert "Manage playlist backups" in result.output
    
    def test_config_help(self):
        """Test config help command."""
        result = self.runner.invoke(cli, ['config', '--help'])
        assert result.exit_code == 0
        assert "Manage configuration" in result.output
    
    def test_template_help(self):
        """Test template help command."""
        result = self.runner.invoke(cli, ['template', '--help'])
        assert result.exit_code == 0
        assert "Manage playlist templates" in result.output
    
    def test_backup_help(self):
        """Test backup help command."""
        result = self.runner.invoke(cli, ['backup', '--help'])
        assert result.exit_code == 0
        assert "Manage playlist backups" in result.output


if __name__ == "__main__":
    pytest.main([__file__])
