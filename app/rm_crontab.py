from crontab import CronTab
from app_global_imports import CURRENT_DIR

script_path = CURRENT_DIR + '/rm_data.py'
temp_log = CURRENT_DIR + '/cron.log'
execute_cmd = 'python ' + script_path + ' --interval 2 >> ' + temp_log
cron_manager  = CronTab(user=True)
job = cron_manager.new(command=execute_cmd)
job.hour.every(1)

cron_manager.write()