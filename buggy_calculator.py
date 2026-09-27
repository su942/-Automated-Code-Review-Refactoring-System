import os

API_KEY = "sk-test-1234567890abcdef"  # BUG(security): hardcoded secret


def divide(a, b):
    return a / b  # BUG(logic): no check for b == 0


def get_user(users, index):
    return users[index]  # BUG(logic): no bounds checking


def run_query(user_input):
    query = "SELECT * FROM users WHERE name = '" + user_input + "'"  # BUG(security): SQL injection
    return query


def calculate_total( items ):
    total = 0
    for i in range(len(items)):          # style: should iterate directly over items
        total = total + items[i]['price']
    return total


class shoppingCart:                       # style: class name should be PascalCase
    def __init__(self):
        self.Items = []                    # style: attribute should be snake_case

    def addItem(self, item):               # style: method should be snake_case
        self.Items.append(item)
        os.system("echo added " + item['name'])  # BUG(security): command injection
