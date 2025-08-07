"""Constants for the IRis IR Remote integration."""

DOMAIN = "iris_ir_remote"

# Configuration
CONF_HOST = "host"
CONF_PORT = "port"
CONF_NAME = "name"
CONF_SCAN_INTERVAL = "scan_interval"

# Default values
DEFAULT_PORT = 80
DEFAULT_NAME = "IRis IR Remote"
DEFAULT_SCAN_INTERVAL = 10  # Reduced from 30 to 10 seconds for more responsive updates

# API endpoints
API_STATUS = "/api/status"
API_BUTTONS = "/api/buttons"
API_TEST = "/api/test"
API_LEARN_START = "/api/learn/start"
API_LEARN_STOP = "/api/learn/stop"
API_LEARN_STATUS = "/api/learn/status"
API_LEARN_SAVE = "/api/learn/save"
API_RESTART = "/api/restart"

# Device info
MANUFACTURER = "IRis"
MODEL = "IR Remote Mini"
