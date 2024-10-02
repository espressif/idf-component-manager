# SPDX-FileCopyrightText: 2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import argparse
import difflib
import glob
import os.path

from gitlab import Gitlab
from prettytable import MARKDOWN, PrettyTable

SAME_STUFF_HTML = '<td>&nbsp;No Differences Found&nbsp;</td>'
COMMENT_HEADER = 'Documentation Diff'


def main(base_folder: str, preview_folder: str, output_dir: str):
    table = PrettyTable()
    table.field_names = ['Base', 'Preview', 'Diff Preview Link']
    table.set_style(MARKDOWN)

    base_folder_html_rel_paths = set(glob.glob('**/*.html', root_dir=base_folder, recursive=True))
    preview_folder_html_rel_paths = set(
        glob.glob('**/*.html', root_dir=preview_folder, recursive=True)
    )
    has_diff = False
    for item in sorted(base_folder_html_rel_paths | preview_folder_html_rel_paths):
        base_name = item if item in base_folder_html_rel_paths else ''
        preview_name = item if item in preview_folder_html_rel_paths else ''
        diff_url = ''

        if base_name and preview_name:
            with (
                open(os.path.join(base_folder, item), 'r') as base_file,
                open(os.path.join(preview_folder, item), 'r') as preview_file,
            ):
                base_lines = base_file.readlines()
                preview_lines = preview_file.readlines()

            diff = difflib.HtmlDiff().make_file(
                fromlines=base_lines,
                tolines=preview_lines,
                fromdesc=base_file.name,
                todesc=preview_file.name,
                context=True,
            )

            if SAME_STUFF_HTML not in diff:
                output_file = os.path.join(output_dir, item)
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'w') as fw:
                    fw.write(diff)

                diff_url = f'{os.getenv("GITLAB_PAGE_HTTPS_URL")}/-/idf-component-manager/-/jobs/{os.getenv("CI_JOB_ID")}/artifacts/{output_file}'
                has_diff = True

        table.add_row([base_name, preview_name, diff_url])

    if not has_diff:
        table = 'No differences found'

    print(table)
    if os.getenv('CI_JOB_ID'):
        post_mr_comment(table)


def post_mr_comment(table: PrettyTable):
    mr = (
        Gitlab(os.getenv('CI_SERVER_URL'), private_token=os.getenv('PROJECT_API_TOKEN'))
        .projects.get(os.getenv('CI_PROJECT_ID'))
        .mergerequests.get(os.getenv('CI_MERGE_REQUEST_IID'))
    )

    # create comment or update existing one with COMMENT_HEADER
    for comment in mr.notes.list():
        if comment.body.startswith(COMMENT_HEADER):
            comment.body = f'{COMMENT_HEADER}\n\n{table}'
            comment.save()
            return
    else:
        mr.notes.create({'body': f'{COMMENT_HEADER}\n\n{table}'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Diff documentation HTML files')
    parser.add_argument('base_folder', help='Base folder')
    parser.add_argument('preview_folder', help='Preview folder')
    parser.add_argument('--output', default='html_diff', help='Output dir')
    args = parser.parse_args()

    main(args.base_folder, args.preview_folder, args.output)
