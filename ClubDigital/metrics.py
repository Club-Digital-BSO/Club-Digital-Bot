from prometheus_client import Histogram, Enum, Gauge, Counter

PROCESS_TIME = Histogram("bot_process_time", "Time that the commands take to prcess")
ONLINE_STATE = Enum('bot_online_state', 'Is the Bot online', states=['starting', 'online', 'offline', 'stopping', 'stopped'])
DATABASE_CONNECTED = Gauge('bot_main_database_connected', 'Databse connection status for the main bot.')
COMMAND_COUNT = Counter('bot_command_count', 'Number of commands executed.')