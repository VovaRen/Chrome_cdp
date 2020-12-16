from util import get_processes, kill_processes
import json
import requests
import trio
import time
from pywinauto import Application
from trio_cdp import open_cdp, dom, page, target, generated, accessibility, schema


# ССЫЛКА НА ДОКУМЕНТАЦИЮ: "https://py-cdp.readthedocs.io/en/latest/api/dom.html#commands" и
# "https://chromedevtools.github.io/devtools-protocol/tot/DOM/" и
# "https://trio-cdp.readthedocs.io/en/latest/"


def run_chrome():
    # закрываем хром, если запущен, и открываем заного с нужным настройками
    pid = get_processes('chrome.exe')
    kill_processes(pid)
    chrome_dir = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    chrome = Application(backend='uia')
    chrome.start(chrome_dir + ' --remote-debugging-port=9222 --force-renderer-accessibility')
    time.sleep(2)


def ws_url_val():
    # поиск websocket url браузера для порта 9222
    tab_list = json.loads(requests.get("http://%s:%s/json" % ("localhost", 9222)).text)
    ws_url = tab_list[0]['webSocketDebuggerUrl']
    return ws_url


async def dom_tree():
    # utl вкладки, потом сделать параметром функции и передавать извне
    target_url = "https://refactoring.guru/ru/design-patterns/python"

    # подключение к браузеру и поиск вкладок
    async with open_cdp(ws_url_val()) as conn:
        targets = await target.get_targets()

    # в списке всех вкладок ищем вкладку с нужным url
        target_id = None
        for t in targets:
            if t.type_ == 'page' and not t.url.startswith('devtools://') and t.url == target_url:
                target_id = t.target_id

        # если вкладка не найдена открываем новую с нужным url
        if not target_id:
            new_page = await target.create_target(target_url)
            target_id = new_page

        # иключение, если вкладка по какой-то причине не открыта или не найдена
        if not target_id:
            raise Exception("Указанная вкладка не открыта!")

        async with conn.open_session(target_id) as session:

            # Включает агент DOM для данной страницы и дожидаемся полной загрузки вкладки
            await page.enable()
            async with session.wait_for(page.LoadEventFired):
                await page.navigate(target_url)

                # получаем всё деревно доступности
                root_node = await accessibility.get_full_ax_tree()

                # корневой узел и поддерево
                root_node1 = await dom.get_document(depth=-1)
                print(root_node)
                print(root_node1)

                # html
                html = await dom.get_outer_html()
                print(html)


if __name__ == '__main__':
    run_chrome()
    ws_url_val()
    trio.run(dom_tree, restrict_keyboard_interrupt_to_checkpoints=True)
