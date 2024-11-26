# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from pathlib import Path
from odoo_module_migrate.base_migration_script import BaseMigrationScript
import re
import lxml.etree as et


def replace_get_view(module_path: Path):
    """
    Replace fields_view_get by get_view
    """
    py_files = list(module_path.rglob("*.py"))
    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        fields_view_get = content.replace("fields_view_get", "get_view")
        if content != fields_view_get:
            file_path.write_text(fields_view_get, encoding="utf-8")


def replace_get_xml_id(module_path: Path):
    """
    Replace get_xml_id by get_external_id
    """
    py_files = list(module_path.rglob("*.py"))
    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        fields_view_get = content.replace("get_xml_id", "get_external_id")
        if content != fields_view_get:
            file_path.write_text(fields_view_get, encoding="utf-8")


def replace_invalidate_cache(module_path: Path):
    """
    Replace get_xml_id by get_external_id
    """
    py_files = list(module_path.rglob("*.py"))
    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        fields_view_get = content.replace("invalidate_cache", "invalidate_recordset")
        if content != fields_view_get:
            file_path.write_text(fields_view_get, encoding="utf-8")


def replace_groups_id(module_path: Path):
    """
    Replace groups_id by groups
    """
    parser = et.XMLParser(remove_blank_text=True)
    tree = et.parse(str(module_path.resolve()), parser)
    root = tree.getroot()

    updated = False
    for elem in root.iter():
        for attr_name in ("groups_id"):
            if attr_name in elem.attrib:
                elem.set("groups", elem.attrib.pop(attr_name))
                updated = True
    if updated:
        module_path.write_text(et.tostring(tree, pretty_print=True, encoding="unicode"))
        return module_path
    return None


def replace_deprecated_flush_methods(module_path: Path):
    """
    Replace deprecated methods 'flush()' and 'recompute()'
    with 'flush_model()', 'flush_recordset()', or 'env.flush_all()' as needed.
    """
    # Get all .py files in the module directory recursively
    py_files = list(module_path.rglob("*.py"))
    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        updated_content = content.replace("flush()", "flush_model()")
        updated_content = updated_content.replace("recompute()", "flush_recordset()")

        if content != updated_content:
            file_path.write_text(updated_content, encoding="utf-8")


def _get_files(module_path, reformat_file_ext):
    """Get files to be reformatted."""
    file_paths = list()
    if not module_path.is_dir():
        raise Exception(f"'{module_path}' is not a directory")
    file_paths.extend(module_path.rglob("*" + reformat_file_ext))
    return file_paths


def reformat_deprecated_tags_py(
        logger, module_path, module_name, manifest_path, migration_steps, tools
):
    """
    Reformat deprecated tags in XML files.
    """
    reformat_file_ext = ".py"
    file_paths = _get_files(module_path, reformat_file_ext)
    logger.debug(f"{reformat_file_ext} files found:\n" f"{list(map(str, file_paths))}")

    replace_get_view(module_path)
    replace_get_xml_id(module_path)
    replace_invalidate_cache(module_path)
    replace_deprecated_flush_methods(module_path)


def reformat_deprecated_tags_xml(
        logger, module_path, module_name, manifest_path, migration_steps, tools
):
    """
    Reformat deprecated tags in XML files.
    """
    reformat_file_ext = ".xml"
    file_paths = _get_files(module_path, reformat_file_ext)
    logger.debug(f"{reformat_file_ext} files found:\n" f"{list(map(str, file_paths))}")

    for file_path in file_paths:
        replace_groups_id(file_path)


class MigrationScript(BaseMigrationScript):
    _GLOBAL_FUNCTIONS = [reformat_deprecated_tags_xml, reformat_deprecated_tags_py]
