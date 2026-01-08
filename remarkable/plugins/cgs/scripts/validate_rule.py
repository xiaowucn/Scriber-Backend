import csv
from collections import defaultdict

from remarkable.checker.helpers import audit_file_rules
from remarkable.common.util import loop_wrapper
from remarkable.db import peewee_transaction_wrapper


class RuleDocValidator:
    """
    工具类, 不存在于业务流程中
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.rules = self.read_rules(file_path)

    @classmethod
    def read_rules(cls, file_path):
        mapping = defaultdict(list)
        with open(file_path, 'rt', encoding='utf-8') as file:
            csv_file = csv.reader(file)
            for line in csv_file:
                _type = line[ord('R') - ord('A')]
                _id = line[0]
                if '开发' in _type:
                    # print(_id)
                    # print(f'"origin": "{origin}",')
                    mapping[_id].append(
                        {
                            'related_name': line[4].strip(),
                            'name': line[10].strip().rstrip('。').replace('\n', ''),
                            'origin': line[1].replace('\n', '').strip(),
                            'from': line[3].replace('\n', '').strip(),
                        }
                    )
                    if _id == '0':
                        continue

            for _id, items in list(mapping.items()):
                if len(items) > 1:
                    mapping.pop(_id)
                    for index, item in enumerate(items, start=1):
                        mapping[f'{_id}_{index}'] = item
                        item['id'] = f'{_id}_{index}'
                        # names = [name.strip() for name in re.compile(r'[12345]、').split(item['name']) if name]
                        # if index <= len(names):
                        #     item['name'] = names[index-1]
                        # else:
                        #     item['name'] = names[-1]
                else:
                    mapping[_id] = items[0]
                    mapping[_id]['id'] = _id

        return mapping

    @loop_wrapper
    
    async def validate(self, fid):
        results = await audit_file_rules(fid)  # 做该检查时可注释掉check_by_rules, 以节约时间

        def get_detail(result_item):
            item_type, item_id, *sub_ids = result_item.label.split('_')
            sub_id = 0 if not sub_ids else sub_ids[0]
            return int(item_id), int(sub_id), item_type

        res = sorted([(item, get_detail(item)) for item in results], key=lambda x: x[1])

        count = 0
        no_matched_name = 0
        for item, (_id, _sub_id, _type) in res:
            _id = str(_id)
            if _sub_id:
                _id = f'{_id}_{_sub_id}'

            if _type not in ('template', 'schema'):
                continue

            if _id in self.rules:
                if item.related_name != self.rules[_id]['related_name']:
                    print(f'+++error related_name: {_id}')
                    print('+', item.related_name)
                    print('-', self.rules[_id]['related_name'])
                    no_matched_name += 1
                if item.name != self.rules[_id]['name']:
                    print(f'+++error name: {_id}')
                    print('+', item.name)
                    print('-', self.rules[_id]['name'])
                    no_matched_name += 1
                if item.origin_contents[0] != '《{}》'.format(self.rules[_id]['from']):
                    print(f'+++error from: {_id}')
                    print('+', item.origin_contents[0])
                    print('-', self.rules[_id]['from'])
                if item.origin_contents[1].strip().replace('\n', '') not in self.rules[_id]['origin']:
                    print(f'+++error origin: {_id}')
                    print('+', item.origin_contents[1].replace('\n', ''))
                    print('-', self.rules[_id]['origin'])
            else:
                print(f'+++ miss {item.label}, {item.name}')

            count += 1

        print(f'name no matched count: {no_matched_name}')
        print(f'all count: {count}')


if __name__ == '__main__':
    validator = RuleDocValidator(file_path='/tmp/1.csv')
    validator.validate(597)
