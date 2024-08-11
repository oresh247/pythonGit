# coding:utf-8
import json
import requests
import configparser
import warnings
import sys
import os
from git import Repo
import subprocess
import re
import pandas as pd
import numpy as np
import html

warnings.filterwarnings("ignore")

config = configparser.ConfigParser()
configJira = configparser.ConfigParser()
config.read("config.ini", encoding='utf-8')
configJira.read("configFields.ini", encoding='utf-8')


# СФЕРА параметры
devUser = config["SFERAUSER"]["devUser"]
devPassword = config["SFERAUSER"]["devPassword"]
sferaUrl = config["SFERA"]["sferaUrl"]
sferaUrlLogin = config["SFERA"]["sferaUrlLogin"]
sferaTestCaseUrl = config["SFERA"]["sferaTestCaseUrl"]
sferaTSectionsUrl = config["SFERA"]["sferaTSectionsUrl"]
sferaSprintUrl = config["SFERA"]["sferaSprintUrl"]
sferaUrlSearch = config["SFERA"]["sferaUrlSearch"]
sferaUrlKnowledge = config["SFERA"]["sferaUrlKnowledge"]
sferaUrlKnowledge2 = config["SFERA"]["sferaUrlKnowledge2"]
sferaUrlRelations = config["SFERA"]["sferaUrlRelations"]
sferaUrlEntityViews = config["SFERA"]["sferaUrlEntityViews"]
sferaUrlSkmbRepos = config["SFERA"]["sferaUrlSkmbRepos"]
sferaUrlDelete = config["SFERA"]["sferaUrlDelete"]

GIT_LINK = config["GIT"]["GIT_LINK"]
GIT_PATH = config["GIT"]["GIT_PATH"]
GIT_BRANCH_PREFIX = config["GIT"]["GIT_BRANCH_PREFIX"]
GIT_MAIN_BRANCH = config["GIT"]["GIT_MAIN_BRANCH"]
MICROSERVICES_LST = json.loads(config["GIT"]["MICROSERVICES_LST"])

session = requests.Session()
session.post(sferaUrlLogin, json={"username": devUser, "password": devPassword}, verify=False)


def get_repo(repo_url, clone_path):
    """Получает репозиторий из указанного URL или открывает существующий."""
    if os.path.exists(clone_path):
        try:
            print(f"Использование существующего каталога: {clone_path}...")
            repo = Repo(clone_path)
            return repo
        except Exception as e:
            print(f"Ошибка при открытии существующего репозитория: {e}")
            sys.exit(1)
    else:
        # Клонирование репозитория
        try:
            print(f"Клонирование репозитория из {repo_url} в {clone_path}...")
            #repo = Repo.clone_from(repo_url, clone_path, branch='develop', single_branch=True)
            repo = Repo.clone_from(repo_url, clone_path, branch='develop')
            return repo
        except Exception as e:
            print(f"Ошибка при клонировании репозитория: {e}")
            sys.exit(1)


def update_repo(repo):
    """Обновляет локальный репозиторий из удаленного."""
    try:
        # Получение изменений из удаленного репозитория
        print("Получение изменений из удаленного репозитория...")
        repo.remotes.origin.fetch()

        # Обновление текущей ветки
        print("Обновление текущей ветки...")
        repo.git.pull()
        print("Репозиторий успешно обновлен.")
    except Exception as e:
        print(f"Ошибка при обновлении репозитория: {e}")
    return repo


def get_latest_tag(repo):
    """Получает последний тег на ветке 'develop' из указанного репозитория."""
    # Получение всех тегов
    tags = repo.tags

    # Поиск последнего тега на ветке develop
    latest_tag = None
    for tag in tags:
        print(tag)
        if tag.commit in repo.head.commit.iter_parents():
            latest_tag = tag
    return latest_tag


def get_tags_for_branch(repo, branch_name):
    """Возвращает список тегов, связанных с указанной веткой."""
    if 'origin/' in branch_name:
        branch_name = branch_name.replace('origin/','')
    # Регулярное выражение для формата 'X.Y.Z'
    pattern = re.compile(r'^\d+\.\d+\.\d+$')
    #pattern = re.compile(r'[a-zA-Z_]+\d+\.\d+\.\d+$')
    #pattern = re.compile(r'^release.*\d+\.\d+\.\d+$')
    #pattern = re.compile(r'^\d+\.\d+\.\d+$|^release.*\d+\.\d+\.\d+$')

    branch = repo.heads[branch_name]  # Получаем объект ветки
    commits_in_branch = list(repo.iter_commits(branch))  # Получаем коммиты в ветке

    # Получаем все теги
    tags = repo.tags
    related_tags = []

    # Проверяем каждый тег, чтобы увидеть, указывает ли он на коммит в ветке
    # Поиск последнего тега на ветке branch_name
    latest_tag = None
    for tag in tags:
        if tag.commit in commits_in_branch and pattern.match(tag.name):
            latest_tag = tag
            #related_tags.append(tag.name)

    return latest_tag


def get_latest_tag_without_download(repo_url):
    # Выполнение команды git ls-remote для получения тегов
    try:
        print(f"Получение тегов из {repo_url}...")
        result = subprocess.run(
            ['git', 'ls-remote', '--tags', repo_url],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")
        sys.exit(1)

    # Обработка вывода для получения последнего тега
    tags = result.stdout.strip().split('\n')
    latest_tag = None

    # Регулярное выражение для фильтрации тегов
    # tag_pattern = re.compile(r'(?P<commit>[0-9a-f]{40})\s+refs/tags/(?P<tag>(\d{4}\.\d{1,2}\.\d{1,2}))(\^{})?$')
    tag_pattern = re.compile(r'(?P<commit>[0-9a-f]{40})\s+refs/tags/(?P<tag>(\d{4}\.\d{1,2}\.\d{1,2}))\^\{\}$')

    for line in tags:
        print(line)
        match = tag_pattern.match(line)
        if match:
            commit_hash = match.group('commit')
            tag_name = match.group('tag')
            # Здесь можно добавить логику для определения "последнего" тега
            # Например, если теги имеют семантическое версионирование, можно использовать их
            if latest_tag is None or tag_name > latest_tag:
                latest_tag = tag_name

    if latest_tag:
        print(f"Последний тег: {latest_tag}")
    else:
        print("Теги не найдены.")


def switch_to_branch(repo, branch_name):
    """Переключается на указанную ветку."""
    if 'origin/' in branch_name:
        branch_name = branch_name.replace('origin/','')
    # Проверяем, существует ли ветка в локальных ветках
    if branch_name in repo.branches:
        branch = repo.heads[branch_name]
        repo.git.checkout(branch)
        print(f"\nПереключено на локальную ветку '{branch_name}'.")
        print(f"Активная ветка '{repo.active_branch.name}'")
        return True

    # Проверяем, существует ли ветка в удаленных репозиториях
    remote_branch_name = f'origin/{branch_name}'  # Формируем имя удаленной ветки
    print(repo.remotes.origin.refs)
    if any(ref.name == remote_branch_name for ref in repo.remotes.origin.refs):
        # Создаем локальную ветку на основе удаленной и переключаемся на нее
        repo.git.checkout('-b', branch_name, remote_branch_name)
        print(f"Переключено на удаленную ветку '{remote_branch_name}' и создана локальная ветка '{branch_name}'.")
        print(f"Активная ветка '{repo.active_branch.name}'")
        return True

    print(f"Ветка '{branch_name}' не найдена.")
    return False


def update_develop_branch(repo):
    """Обновляет локальную ветку develop."""
    print("Обновление ветки 'develop'...")
    repo.git.pull()


def get_unmerged_branches(repo, branch_name):
    """Возвращает список веток, которые не были слиты с веткой develop."""
    # Получаем список всех веток, которые не были слиты с веткой origin/develop
    unmerged_branches = repo.git.branch('-r', '--no-merged', branch_name).splitlines()

    # Очищаем список от лишних пробелов и символов
    unmerged_branches = [branch.strip() for branch in unmerged_branches]
    print(f"Cписок всех веток, которые не были слиты с веткой '{branch_name}' =  '{unmerged_branches}'")
    return unmerged_branches


def filter_release_branches(branches):
    """Возвращает список строк, содержащих подстроку 'release'."""
    return [branch for branch in branches if ('release' in branch)]


def get_file_from_repo(repo, file_name):
    """Возвращает содержимое указанного файла из репозитория."""
    try:
        # Получаем текущую ветку
        current_branch = repo.active_branch.name

        # Получаем объект файла в текущей ветке
        file_path = os.path.join(repo.working_tree_dir, file_name)

        # Проверяем, существует ли файл
        if os.path.isfile(file_path):
            with open(file_path, 'r') as file:
                content = file.read()
            return content
        else:
            return f"Файл '{file_name}' не найден в ветке '{current_branch}'."

    except Exception as e:
        return f"Ошибка при получении файла: {e}"


def get_service_git_info(service_name, df):
    clone_path = GIT_PATH + service_name
    repo_url = GIT_LINK + service_name + '.git'
    row = {col: '' for col in df.columns.tolist()}
    row['service'] = service_name


    repo = get_repo(repo_url, clone_path)
    #switch_to_branch(repo, GIT_MAIN_BRANCH)
    #repo = update_repo(repo)

    unmerged_branches = get_unmerged_branches(repo, GIT_BRANCH_PREFIX + GIT_MAIN_BRANCH)
    unmerged_branches_release = filter_release_branches(unmerged_branches)
    print(f"Cписок всех релизных веток, которые не были слиты с веткой '{GIT_MAIN_BRANCH}' =  '{unmerged_branches_release}'")
    unmerged_branches_release.append(GIT_BRANCH_PREFIX+GIT_MAIN_BRANCH)
    not_merged_branch_lst = unmerged_branches.copy()

    print(f"\nСбор информации по следующим веткам =  '{unmerged_branches_release}'")

    for branche in reversed(unmerged_branches_release):
        if switch_to_branch(repo, branche):
            if GIT_MAIN_BRANCH in branche:
                separator = ''
            else: separator = ',<br>'

            repo = update_repo(repo)
            file_content1 = get_file_from_repo(repo, 'build.gradle')
            file_content2 = get_file_from_repo(repo, 'gradle.properties')
            skmb_reactive_dto = get_version(file_content1, file_content2, 'skmb-reactive-dto')
            skmb_monitoring_event_lib = get_version(file_content1, file_content2, 'skmb-monitoring-event-lib')
            skmb_logging_commons = get_version(file_content1, file_content2, 'skmb-logging-commons')
            skmb_common_settings_controller = get_version(file_content1, file_content2, 'skmb-common-settings-controller')

            row['skmb_reactive_dto'] = row['skmb_reactive_dto'] + separator + branche + ':=' + skmb_reactive_dto
            row['skmb_monitoring_event_lib'] = row['skmb_monitoring_event_lib'] + separator + branche + ':=' + skmb_monitoring_event_lib
            row['skmb_logging_commons'] = row['skmb_logging_commons'] + separator + branche + ':=' + skmb_logging_commons
            row['skmb_common_settings_controller'] = row['skmb_common_settings_controller'] + separator + branche + ':=' + skmb_common_settings_controller

            print(f"верксия бтблиотеки skmb_reactive_dto:'{skmb_reactive_dto}'")
            print(f"верксия бтблиотеки skmb_monitoring_event_lib:'{skmb_monitoring_event_lib}'")
            print(f"верксия бтблиотеки skmb_logging_commons:'{skmb_logging_commons}'")
            print(f"верксия бтблиотеки skmb_common_settings_controller:'{skmb_common_settings_controller}'")

            unmerged_branches = get_unmerged_branches(repo, branche)
            not_merged_branch_lst = list(set(not_merged_branch_lst) & set(unmerged_branches))

            latest_tag = get_tags_for_branch(repo, branche)

            row['latest_tag'] = row['latest_tag'] + separator + branche + ':=' + str(latest_tag)
            print(f"Последний тег:'{latest_tag}'")

    not_merged_branches_str = '<br>'.join(not_merged_branch_lst)
    row['not_merged_branch_lst'] = row['not_merged_branch_lst'] + not_merged_branches_str
    print(f"\nОтдельные ветки  =  '{not_merged_branches_str}'")
    # Добавление строки с использованием pd.concat()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    return df


def get_version(text1, text2, lib_name):
    pattern1 = r'\S*\s*' + lib_name + '\s*:\s*(\S+)'
    match1 = re.search(pattern1, text1)
    if match1:
        result = match1.group(1)
        if '$' in result:
            pattern2 = r'\$\{(\S+)\}'
            match2 = re.search(pattern2, result)
            if match2:
                result = match2.group(1)   # Возвращаем значение внутри фигурных скобок
                pattern3 = result + r'\s*=\s*(\S+)'
                match3 = re.search(pattern3, text2)
                if match3:
                    result = match3.group(1)

        result = result.replace('"', '')
        result = result.replace("'", '')

        return result  # Возвращаем версию из implementation
    return ''  # Если ни одна версия не найдена


def generate_release_html(df):
    # Генерируем HTML-код
    html_code = df.to_html(index=False)
    print(html_code)

    # Декодируем HTML-спецсимволы
    decoded_html = html.unescape(html_code)
    decoded_html = str.replace(decoded_html, '\\n', '')
    decoded_html = str.replace(decoded_html, '\n', '')
    decoded_html = str.replace(decoded_html, 'origin/', '')
    decoded_html = str.replace(decoded_html, '"', '')
    decoded_html = str.replace(decoded_html, "'", '"')
    # decoded_html = str.replace(decoded_html, 'class=sfera-link sfera-task sfera-link-style',
    #                            'class="sfera-link sfera-task sfera-link-style"')
    # decoded_html = str.replace(decoded_html, '<table border=1 class=dataframe>',
    #                            '<table class="MsoNormalTable" border="1" cellspacing="0" cellpadding="0" width="1440" data-widthmode="wide" data-lastwidth="1761px" style="border-collapse: collapse; width: 1761px;" id="mce_1">')
    decoded_html = str.replace(decoded_html, '<table border=1 class=dataframe>',
                               '<table border=1 style="border-collapse: collapse; width: 1800px;" id="mce_1-1723402032896-98" data-rtc-uid="244a0614-0d0b-42fd-b8af-5992e9fb70be">')

    return decoded_html


def replace_release_html(html, page_id):
    url1 = sferaUrlKnowledge + 'cid/' + page_id
    response = session.get(url1, verify=False)
    id = json.loads(response.text)['payload']['id']
    data = {
        "id": id,
        "content": html,
        "name": 'ОКР.Микросервисы'
    }
    url2 =sferaUrlKnowledge2 + '/' + page_id
    response = session.patch(url2, json=data, verify=False)
    if response.ok != True:
        raise Exception("Error creating story " + response)
    return json.loads(response.text)


def publication_release_html(html, parentPage, page_name):
    data = {
        "spaceId": "cbbcfa0b-0542-4407-9e49-61c6aa7caf1b",
        "parentCid": parentPage,
        "name": page_name,
        "content": html
    }
    response = session.post(sferaUrlKnowledge2, json=data, verify=False)
    if response.ok != True:
        raise Exception("Error creating story " + response)
    return json.loads(response.text)

def generating_release_page(microservices_lst, page_id):
    # Создаем пустой DataFrame с указанными колонками
    columns = [
        'service',
        'latest_tag',
        'not_merged_branch_lst',
        'skmb_reactive_dto',
        'skmb_logging_commons',
        'skmb_common_settings_controller',
        'skmb_monitoring_event_lib'
    ]
    df = pd.DataFrame(columns=columns)
    for microservice in microservices_lst:
        df = get_service_git_info(microservice, df)

    pd.set_option('display.width', 320)
    pd.set_option('display.max_columns', 20)
    np.set_printoptions(linewidth=320)
    print(df)
    # Формируем HTML таблицу
    html = generate_release_html(df)
    print(html)
    replace_release_html(html, page_id)
    #publication_release_html(html, '1263114', 'ОКР.Микросервисы')


page_id = '1318737'
generating_release_page(MICROSERVICES_LST, page_id)


