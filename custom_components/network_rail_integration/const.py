"""Constants for the Network Rail integration."""

DOMAIN = "homeassistant_network_rail_uk"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_TOPIC = "topic"
CONF_STANOX_FILTER = "stanox_filter"
CONF_STATIONS = "stations"  # List of station configs
CONF_TOC_FILTER = "toc_filter"
CONF_EVENT_TYPES = "event_types"
CONF_FIX_DST_QUIRK = "fix_dst_quirk"
CONF_ENABLE_TD = "enable_td"  # Enable Train Describer feed
CONF_TD_AREAS = "td_areas"  # List of TD area IDs to track
CONF_TD_EVENT_HISTORY_SIZE = "td_event_history_size"  # Number of events to keep per area
CONF_DIAGRAM_CONFIGS = "diagram_configs"  # List of diagram configurations
# Deprecated constants (kept for migration)
CONF_DIAGRAM_ENABLED = "diagram_enabled"
CONF_DIAGRAM_STANOX = "diagram_stanox"
CONF_DIAGRAM_RANGE = "diagram_range"  # Number of stations each direction

# Track Section Monitor configuration
CONF_TRACK_SECTIONS = "track_sections"  # List of track section configs
CONF_TRACK_SECTION_NAME = "track_section_name"
CONF_TRACK_SECTION_CENTER_STANOX = "center_stanox"
CONF_TRACK_SECTION_BERTH_RANGE = "berth_range"
CONF_TRACK_SECTION_TD_AREAS = "td_areas"
CONF_TRACK_SECTION_ALERT_SERVICES = "alert_services"

# VSTP configuration
CONF_ENABLE_VSTP = "enable_vstp"  # Enable VSTP feed

# Default Train Describer event history size
DEFAULT_TD_EVENT_HISTORY_SIZE = 10

DEFAULT_TOPIC = "TRAIN_MVT_ALL_TOC"
DEFAULT_TD_TOPIC = "TD_ALL_SIG_AREA"
DEFAULT_VSTP_TOPIC = "VSTP_ALL"

NR_HOST = "publicdatafeeds.networkrail.co.uk"
NR_PORT = 61618

SMART_DATA_URL = "https://publicdatafeeds.networkrail.co.uk/ntrod/SupportingFileAuthenticate?type=SMART"
SMART_CACHE_FILE = "smart_data.json"
SMART_CACHE_EXPIRY_DAYS = 30

DISPATCH_MOVEMENT = f"{DOMAIN}_movement"
DISPATCH_CONNECTED = f"{DOMAIN}_connected"
DISPATCH_TD = f"{DOMAIN}_td"  # Train Describer messages
DISPATCH_VSTP = f"{DOMAIN}_vstp"  # VSTP schedule messages
DISPATCH_TRACK_SECTION = f"{DOMAIN}_track_section"  # Track section events
