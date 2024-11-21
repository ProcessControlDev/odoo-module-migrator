# Copyright (C) 2024 - Today: NextERP Romania (https://nexterp.ro)
# @author: Mihai Fekete (https://github.com/NextERP-Romania)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from pathlib import Path
import json
import lxml.etree as et
import os
import re

from odoo_module_migrate.base_migration_script import BaseMigrationScript


# Following https://github.com/OCA/maintainer-tools/wiki/Migration-to-version-15.0

def add_asset_to_manifest(assets, manifest):
    """Add an asset to a manifest file."""
    if "assets" not in manifest:
        manifest["assets"] = {}
    for asset_type, asset_files in assets.items():
        if asset_type not in manifest["assets"]:
            manifest["assets"][asset_type] = []
        manifest["assets"][asset_type].extend(asset_files)


def remove_asset_file_from_manifest(file, manifest):
    """Remove asset file from manifest views."""
    if "data" not in manifest:
        return
    for file_path in manifest["data"]:
        if file_path == file:
            manifest["data"].remove(file)


def remove_node_from_xml(record_node, node):
    """Remove a node from an XML tree."""
    to_remove = True
    if node.getchildren():
        to_remove = False
    if to_remove:
        parent = node.getparent() if node.getparent() is not None else record_node
        parent.remove(node)


def reformat_assets_definition(
        logger, module_path, module_name, manifest_path, migration_steps, tools
):
    """Reformat assets declaration in XML files."""

    manifest = tools._get_manifest_dict(manifest_path)
    parser = et.XMLParser(remove_blank_text=True)
    assets_views = [
        "web.assets_backend",
        "web.assets_common",
        "web.assets_frontend",
        "web.assets_qweb",
        "web.assets_tests",
        "website.assets_frontend",
        "website.assets_editor",
        "website.assets_frontend_editor",
        "website.assets_wysiwyg",
        "web_enterprise.assets_backend",
        "web_enterprise.assets_common",
        "web_enterprise._assets_backend_helpers",
    ]
    for file_path in manifest.get("data", []):
        if not file_path.endswith(".xml"):
            continue
        xml_file = open(os.path.join(module_path, file_path), "r")
        tree = et.parse(xml_file, parser)
        record_node = tree.getroot()
        for node in record_node.getchildren():
            if node.get("inherit_id") in assets_views:
                for xpath_elem in node.xpath("xpath[@expr]"):
                    for file in xpath_elem.getchildren():
                        elem_file_path = False
                        if file.get("src"):
                            elem_file_path = ["".join(file.get("src"))]
                        elif file.get("href"):
                            elem_file_path = ["".join(file.get("href"))]
                        if elem_file_path:
                            add_asset_to_manifest(
                                {node.get("inherit_id"): elem_file_path},
                                manifest,
                            )
                            remove_node_from_xml(record_node, file)
                    remove_node_from_xml(record_node, xpath_elem)
            remove_node_from_xml(record_node, node)
        # write back the node to the XML file
        with open(os.path.join(module_path, file_path), "wb") as f:
            et.indent(tree)
            tree.write(f, encoding="utf-8", xml_declaration=True)
        if not record_node.getchildren():
            remove_asset_file_from_manifest(file_path, manifest)
            os.remove(os.path.join(module_path, file_path))
    manifest_content = json.dumps(manifest, indent=4, default=str)
    manifest_content = manifest_content.replace(": true", ": True").replace(
        ": false", ": False"
    )
    tools._write_content(manifest_path, manifest_content)


def _replace_t_esc_and_t_raw_with_t_out(file_path: Path):
    """
    Replaces `t-esc` and `t-raw` attributes with `t-out` in an XML file.

    Args:
        file_path (Path): Path to the XML file to process.

    Returns:
        Path: The updated file if changes were made, otherwise None.
    """
    parser = et.XMLParser(remove_blank_text=True)
    tree = et.parse(str(file_path.resolve()), parser)
    root = tree.getroot()

    # Find all elements with `t-esc` or `t-raw` attributes
    updated = False
    for elem in root.iter():
        for attr_name in ("t-esc", "t-raw"):
            if attr_name in elem.attrib:
                # Replace with `t-out`
                elem.set("t-out", elem.attrib.pop(attr_name))
                updated = True
    if updated:
        # Write back the modified XML
        file_path.write_text(et.tostring(tree, pretty_print=True, encoding="unicode"))
        return file_path
    return None


def _get_files(module_path, reformat_file_ext):
    """Get files to be reformatted."""
    file_paths = list()
    if not module_path.is_dir():
        raise Exception(f"'{module_path}' is not a directory")
    file_paths.extend(module_path.rglob("*" + reformat_file_ext))
    return file_paths


def add_sudo_to_ir_model(module_path: Path):
    """
    Adds `.sudo()` to `'ir.model'` references in Python files when used with `self.env`.

    Args:
        module_path (Path): Path to the module to process.
    """
    py_files = list(module_path.rglob("*.py"))
    pattern = re.compile(r'(self\.env\[\s*["\']ir\.model["\']\s*])(?!\.sudo\(\))')
    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        new_content = pattern.sub(r'\1.sudo()', content)
        if content != new_content:
            file_path.write_text(new_content, encoding="utf-8")


def replace_dollar_braces_in_xml(module_path: Path):
    """
    Replace `${ contenido }` with `{{ contenido }}` in .xml files.

    Args:
        module_path (Path): Path to the directory containing XML files.
    """
    xml_files = list(module_path.rglob("*.xml"))
    for file_path in xml_files:
        content = file_path.read_text(encoding="utf-8")
        new_content = re.sub(r'\$\{(.*?)}', r'{{\1}}', content)
        if content != new_content:
            file_path.write_text(new_content, encoding="utf-8")


def update_manifest_qweb(logger, module_path, module_name, manifest_path, migration_steps, tools):
    """
    Reemplazar la clave 'qweb' en __manifest__.py y mover su contenido a web.assets_qweb.
    Args:
        module_path (Path): Ruta del directorio que contiene los módulos de Odoo.
    """
    manifest_files = list(module_path.rglob("__manifest__.py"))
    for manifest_file in manifest_files:
        # Cargar el diccionario del manifiesto usando _get_manifest_dict
        manifest_dict = tools._get_manifest_dict(manifest_path)

        if 'qweb' in manifest_dict:
            qweb_files = manifest_dict.pop('qweb')
            assets_qweb_files = ', '.join([f"'{file}'" for file in qweb_files])
            if 'assets' not in manifest_dict:
                manifest_dict['assets'] = {}
            if 'web.assets_qweb' not in manifest_dict['assets']:
                manifest_dict['assets']['web.assets_qweb'] = []
            manifest_dict['assets']['web.assets_qweb'].extend(qweb_files)
            with open(manifest_file, 'w', encoding='utf-8') as f:
                f.write(str(manifest_dict))


def reformat_deprecated_tags(
        logger, module_path, module_name, manifest_path, migration_steps, tools
):
    """Reformat deprecated tags in XML files.

    Deprecated tags are `t-esc` and `t-raw`:
    they have to be substituted by the `t-out` tag.
    """
    reformat_file_ext = ".xml"
    file_paths = _get_files(module_path, reformat_file_ext)
    logger.debug(f"{reformat_file_ext} files found:\n" f"{list(map(str, file_paths))}")

    reformatted_files = list()
    for file_path in file_paths:
        reformatted_file = _replace_t_esc_and_t_raw_with_t_out(file_path)
        if reformatted_file:
            reformatted_files.append(reformatted_file)
    logger.debug("Reformatted files:\n" f"{list(reformatted_files)}")
    replace_savepoint_case(module_path)
    add_sudo_to_ir_model(module_path)
    replace_dollar_braces_in_xml(module_path)


def replace_savepoint_case(module_path: Path):
    """
    Replaces all occurrences of 'SavepointCase' with 'TransactionCase' in .py files.
    Args:
        module_path (Path): Path to the module to process.
    """
    py_files = list(module_path.rglob("*.py"))
    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        new_content = content.replace("SavepointCase", "TransactionCase")
        if content != new_content:
            file_path.write_text(new_content, encoding="utf-8")


class MigrationScript(BaseMigrationScript):
    _GLOBAL_FUNCTIONS = [reformat_assets_definition, reformat_deprecated_tags, update_manifest_qweb]
