from util import get_processes, kill_processes
import json
import requests
import trio
import time
import win32api
import win32con
from ctypes.wintypes import tagPOINT
from pywinauto import Application
from trio_cdp import open_cdp, dom, page, target, generated, accessibility, schema, css


# ССЫЛКА НА ДОКУМЕНТАЦИЮ: "https://py-cdp.readthedocs.io/en/latest/api/dom.html#commands" и
# "https://chromedevtools.github.io/devtools-protocol/tot/DOM/"


def run_chrome():
    # закрываем хром, если запущен, и открываем заного с нужным настройками
    pid = get_processes('chrome.exe')
    kill_processes(pid)
    chrome_dir = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    chrome = Application(backend='uia')
    chrome.start(chrome_dir + ' --remote-debugging-port=9222 --force-renderer-accessibility --start-maximized')
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

                # ПОКА НЕ РАЗОБРАЛСЯ С ОЖИДАНИЕМ ПОЛУЧЕНИЯ ВСЕХ ЭЛЕМЕНТОВ
                time.sleep(10)

                root_node6 = await accessibility.get_full_ax_tree()
                roles_names_coords = []
                for i in root_node6:
                    roles_names_coords.append(i.role.value)
                    if i.name:
                        if i.name.value:
                            roles_names_coords.append(i.name.value)
                        else:
                            roles_names_coords.append('NoName')
                    if not i.name:
                        roles_names_coords.append('NoName')

                    # БЛОК ЗНАЧЕНИЙ (МОЖЕТ ПОНАДОБИТСЯ)
                    # if i.name:
                    #     if i.name.sources:
                    #         if len(i.name.sources) > 2:
                    #             if i.name.sources[2].value:
                    #                 roles_names_coords.append(i.name.sources[2].value.value)
                    #             else:
                    #                 roles_names_coords.append('NoValue')
                    #     else:
                    #         roles_names_coords.append('NoValue')
                    # if not i.name:
                    #     roles_names_coords.append('NoValue')

                    if i.backend_dom_node_id:
                        q = await generated.dom.get_box_model(backend_node_id=i.backend_dom_node_id)
                        roles_names_coords.append((q.content[0] + q.content[2])/2)
                        roles_names_coords.append((q.content[1] + q.content[5])/2)
                    else:
                        roles_names_coords.append('NoCordX')
                        roles_names_coords.append('NoCordY')
                elements_list = (list(zip(*[iter(roles_names_coords)] * 4)))
                for element in set(elements_list):
                    if element[0] == 'link':
                        print(element)

                        # TODO - координаты смещаются из-за заголовка chrome
                        if element[1] == 'Go':
                            chrome = Application(backend='uia').connect(
                                title='Паттерны проектирования на Python - Google Chrome')
                            window_chrome = chrome.window()
                            window_chrome.set_focus()
                            point = tagPOINT(int(element[2]), int(element[3]) + 70)
                            win32api.SetCursorPos((point.x, point.y))
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, int(element[2]),
                                                 int(element[3]), 0, 0)
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, int(element[2]),
                                                 int(element[3]), 0, 0)


if __name__ == '__main__':
    # run_chrome()
    ws_url_val()
    trio.run(dom_tree, restrict_keyboard_interrupt_to_checkpoints=True)
