#!/usr/bin/env python

"""A list of functions to validate config models."""

import logging

import schema

from main.config import const


logger = logging.getLogger(__name__)


valid_connection_types = {
    const.SOURCES: [const.INGESTORS, const.LDPS],
    const.INGESTORS: [const.SINKS],
    const.SMLS: [const.VOTERS, const.SINKS],
    const.VOTERS: [const.LDPS, const.SINKS],
    const.LDPS: [const.SINKS],
    const.SINKS: []
}


valid_feedback_connection_types = {
    const.SOURCES: [],
    const.INGESTORS: [],
    const.SMLS: [],
    const.VOTERS: [],
    const.LDPS: [],
    const.SINKS: [const.VOTERS, const.SMLS]
}


def validate_config(config):
    """Perform the whole validation: schema, uniqueness and connections

    :param config: dict -- configuration to validate
    :raises: SchemaError -- if the configuration is not valid for any reason
    """
    _validate_schema(config)
    _validate_only_one_voter(config)
    _validate_ids_uniqueness(config)
    _validate_connections(config)


def validate_links(links):
    """Validate links to make sure, nothing is missing

    :param links: dict -- connection links to validate
    :raises: SchemaError -- if any link is missing
    """
    missing = set([])
    all_keys = set(links.keys())
    for connections in links.values():
        for component in connections:
            if component not in all_keys:
                missing.add(component.id())
    if len(missing) > 0:
        raise schema.SchemaError([
            "In connections section, the following components are not "
            "connected\n\t{}\n"
            "please modify the configuration so that their list of "
            "connections is at least '[]'".format(", ".join(missing))], [])


def _validate_schema(config):
    """Validate the configuration, with spark, up to the orchestration level

    Checks that hte spark configuration is valid, as well as the modules
    structure in the configuration up to the orchestration level.
    Each module will be responsible to validate its own sub-configuration.

    :param config: dict -- configuration model for the whole system
    :raises: SchemaError -- if the configuration, up to the
    orchestration level, is not valid
    """
    config_schema = schema.Schema({
        "spark_config": {
            "appName": basestring,
            "streaming": {
                "batch_interval": schema.And(int, lambda b: b > 0)
            }
        },
        "server": {
            "port": int,
            "debug": bool
        },
        "sources": {
            schema.Optional(basestring): {basestring: object}
        },
        "ingestors": {
            schema.Optional(basestring): {basestring: object}
        },
        "smls": {
            schema.Optional(basestring): {basestring: object}
        },
        "voters": {
            schema.Optional(basestring): {basestring: object}
        },
        "sinks": {
            schema.Optional(basestring): {basestring: object}
        },
        "ldps": {
            schema.Optional(basestring): {basestring: object}
        },
        "connections": {
            schema.Optional(basestring): [basestring]
        },
        "feedback": {
            schema.Optional(basestring): [basestring]
        }
    })
    return config_schema.validate(config)


def _validate_only_one_voter(config):
    """Check that the configuration defines only a single voter

    :param config: dict -- configuration model for the whole system
    :raises: SchemaError -- if there is more than one voter defined in config
    """
    def _raise(comp):
        raise schema.SchemaError([
            "More than one {} found in the config, please modify " +
            "it specifying only one {}".format(comp, comp)], [])

    if len(config["voters"]) > 1:
        _raise("voter")


def _validate_ids_uniqueness(config):
    """Validate that the IDs of the components are unique

    :param config: dict -- configuration model for the whole system
    :raises: SchemaError -- if there is any duplicated ID in the configuration
    """
    all_ids = set()
    for comp_type in valid_connection_types.keys():
        for com_id in config[comp_type].keys():
            if com_id in all_ids:
                raise schema.SchemaError(
                    ["Duplicated component ID : " + com_id], [])
            all_ids.add(com_id)


def _validate_expected_dest_type(config, from_id, to_ids, expected_types):
    """Check that the connection is valid according to expected_types.

    :param config: dict -- configuration model for the whole system
    :param from_id: str -- ID of the component which is the
    origin point of the connection
    :param to_ids: list -- IDs of the components which are the
    destination points of the connections
    :param expected_types: list -- types of components that are allowed
    as destination points
    """
    for to_id in to_ids:
        logger.debug("validating connection "+from_id+" --> "+to_id)
        valid_connection = False
        for expected_type in expected_types:
            if to_id in config[expected_type].keys():
                valid_connection = True
                break
        if not valid_connection:
            raise schema.SchemaError([
                from_id + " connected to a wrong component: " + to_id +
                ". It should be connected only to any of : " +
                str(expected_types)], [])


def _validate_existing_id(config, component_id):
    """Check that the id passed as parameter is defined in the configuration

    :param config: dict -- configuration model for the whole system
    :param from_id: str -- component ID to be found in configuration
    """
    found_id = False
    for comp_type in valid_connection_types.keys():
        if component_id in config[comp_type].keys():
            found_id = True
    if not found_id:
        raise schema.SchemaError([
            'In "connections", component `{}` hasn\'t been defined'
            .format(component_id)
        ], [])


def _validate_from_dictionary(config, conf_key, validation_dict):
    """Validate connections in config[conf_key] according to validation_dict

    :param config: dict -- configuration model for the whole system
    :param conf_key: str -- key of the configuration dictionary where
    the connections to be checked are defined
    :param validation_dict: dict -- keys are source types, and values
    are lists of allowed destination types for that particular source type
    """
    for from_id in config[conf_key].keys():
        _validate_existing_id(config, from_id)
        to_ids = config[conf_key][from_id]
        for comp_type in validation_dict.keys():
            if from_id in config[comp_type].keys():
                _validate_expected_dest_type(
                    config, from_id, to_ids, validation_dict[comp_type])


def _validate_connections(config):
    """Validate that the connections defined in config are allowed

    :param config: dict -- configuration model for the whole system
    """
    _validate_from_dictionary(config, "connections", valid_connection_types)
    _validate_from_dictionary(config, "feedback",
                              valid_feedback_connection_types)
