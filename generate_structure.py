import os


def generate_project_structure(path, prefix=''):
    items = os.listdir(path)
    for index, item in enumerate(items):
        item_path = os.path.join(path, item)
        is_last = index == len(items) - 1
        if os.path.isdir(item_path):
            print(prefix + ('└── ' if is_last else '├── ') + item + '/')
            new_prefix = prefix + ('    ' if is_last else '│   ')
            generate_project_structure(item_path, new_prefix)
        else:
            print(prefix + ('└── ' if is_last else '├── ') + item)


# 请将此路径替换为你的项目文件夹路径
project_path = '.agent2_sales_qa'
generate_project_structure(project_path)