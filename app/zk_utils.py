from exceptions import *

def get_device_fields(zk_client, device_path):
    if not zk_client.exists(device_path):
        raise ZookeeperServiceException("device path %s doesn't exist" % device_path)
    device_fields = zk_client.get_children(device_path)
    fields_dict = {}
    for field_key in device_fields:
        field_path = device_path + '/' + field_key
        field_value = zk_client.get(field_path)[0].decode('ascii')
        fields_dict[field_key] = field_value
    return fields_dict

def get_all_devices_info(zk_client, root_path):
    info_dict = {}
    if not zk_client.exists(root_path):
        raise ZookeeperServiceException("node doesn't exist")
    device_ids = zk_client.get_children(root_path)
    for device_id in device_ids:
        device_path = root_path + '/' + device_id
        info_dict[device_id] = get_device_fields(zk_client, device_path)
    return info_dict