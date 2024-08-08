import sys
import os
from git import Repo
import send2trash
import subprocess
import re
import git


GIT_LINK = 'ssh://git@git.sfera.inno.local:7999/SKMB/'
GIT_PATH = 'C:\\_GIT\\'


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
            repo = Repo.clone_from(repo_url, clone_path, branch='develop', single_branch=True)
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
        if tag.commit in repo.head.commit.iter_parents():
            latest_tag = tag
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
    if branch_name in repo.branches:
        branch = repo.heads[branch_name]
        repo.git.checkout(branch)
        print(f"Переключено на ветку '{branch_name}'.")
        return True
    else:
        print(f"Ветка '{branch_name}' не найдена.")
        return False


def get_unmerged_branches(repo):
    """Возвращает список веток, которые не были слиты с веткой develop."""
    # Получаем список всех веток, которые не были слиты с текущей веткой (develop)
    unmerged_branches = repo.git.branch('--no-merged').splitlines()

    # Очищаем список от лишних пробелов и символов
    unmerged_branches = [branch.strip() for branch in unmerged_branches]

    return unmerged_branches


def update_develop_branch(repo):
    """Обновляет локальную ветку develop."""
    print("Обновление ветки 'develop'...")
    repo.git.pull()


# service_name = 'skmb-fin-statements-adapter'
# service_name = 'skmb-pim-adapter'
# service_name = 'skmb-credithistory-reactive-service'
# service_name = 'skmb-reactive-dto'
service_name = 'skmb-monitoring-service'
#clone_path = os.path.join(os.getcwd(), service_name)  # Путь для клонирования репозитория
clone_path = GIT_PATH + service_name
repo_url = GIT_LINK + service_name + '.git'
# get_latest_tag_without_download(repo_url)
repo = get_repo(repo_url, clone_path)
repo = update_repo(repo)
latest_tag = get_latest_tag(repo)

if latest_tag:
    print(f"Последний тег на ветке 'develop': {latest_tag}")
else:
    print("Теги на ветке 'develop' не найдены.")

# Переключаемся на ветку develop
switch_to_branch(repo, 'develop')
# Обновляем ветку
update_develop_branch(repo)
# Получаем не слитые ветки
unmerged_branches = get_unmerged_branches(repo)
print("Не слитые ветки:", unmerged_branches)
