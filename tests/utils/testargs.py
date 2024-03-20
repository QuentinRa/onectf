import json

root_args_data = 'data/args/'


def load_args(filename):
    root = 'data/args/'
    base_test_data = {}
    current = root + filename
    while current is not None:
        with open(current) as f:
            json_data = json.load(f)
            if '_include' in json_data:
                current = root + json_data['_include']
            else:
                current = None
            base_test_data.update(json_data)
    return base_test_data
