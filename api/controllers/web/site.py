# -*- coding:utf-8 -*-
import os

from flask_restful import fields, marshal_with
from flask import current_app
from werkzeug.exceptions import Forbidden

from controllers.web import api
from controllers.web.wraps import WebApiResource
from extensions.ext_database import db
from models.model import Site
from services.billing_service import BillingService


class AppSiteApi(WebApiResource):
    """Resource for app sites."""

    model_config_fields = {
        'opening_statement': fields.String,
        'suggested_questions': fields.Raw(attribute='suggested_questions_list'),
        'suggested_questions_after_answer': fields.Raw(attribute='suggested_questions_after_answer_dict'),
        'more_like_this': fields.Raw(attribute='more_like_this_dict'),
        'model': fields.Raw(attribute='model_dict'),
        'user_input_form': fields.Raw(attribute='user_input_form_list'),
        'pre_prompt': fields.String,
    }

    site_fields = {
        'title': fields.String,
        'icon': fields.String,
        'icon_background': fields.String,
        'description': fields.String,
        'copyright': fields.String,
        'privacy_policy': fields.String,
        'default_language': fields.String,
        'prompt_public': fields.Boolean
    }

    app_fields = {
        'app_id': fields.String,
        'end_user_id': fields.String,
        'enable_site': fields.Boolean,
        'site': fields.Nested(site_fields),
        'model_config': fields.Nested(model_config_fields, allow_null=True),
        'plan': fields.String,
        'can_replace_logo': fields.Boolean,
        'custom_config': fields.Raw(attribute='custom_config'),
    }

    @marshal_with(app_fields)
    def get(self, app_model, end_user):
        """Retrieve app site info."""
        # get site
        site = db.session.query(Site).filter(Site.app_id == app_model.id).first()

        if not site:
            raise Forbidden()

        edition = os.environ.get('EDITION')
        can_replace_logo = False

        if edition == 'CLOUD':
            info = BillingService.get_info(app_model.tenant_id)
            can_replace_logo = info['can_replace_logo']

        return AppSiteInfo(app_model.tenant, app_model, site, end_user.id, can_replace_logo)


api.add_resource(AppSiteApi, '/site')


class AppSiteInfo:
    """Class to store site information."""

    def __init__(self, tenant, app, site, end_user, can_replace_logo):
        """Initialize AppSiteInfo instance."""
        self.app_id = app.id
        self.end_user_id = end_user
        self.enable_site = app.enable_site
        self.site = site
        self.model_config = None
        self.plan = tenant.plan
        self.can_replace_logo = can_replace_logo

        if can_replace_logo:
            base_url = current_app.config.get('FILES_URL')
            remove_webapp_brand = tenant.custom_config_dict.get('remove_webapp_brand', False)
            replace_webapp_logo = f'{base_url}/files/workspaces/{tenant.id}/webapp-logo' if tenant.custom_config_dict.get('replace_webapp_logo') else None
            self.custom_config = {
                'remove_webapp_brand': remove_webapp_brand,
                'replace_webapp_logo': replace_webapp_logo,
            }

        if app.enable_site and site.prompt_public:
            app_model_config = app.app_model_config
            self.model_config = app_model_config
