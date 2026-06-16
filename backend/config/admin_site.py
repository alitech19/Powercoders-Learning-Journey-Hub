"""Custom Django admin site with product-area ordering."""

from __future__ import annotations

from django.contrib.admin import AdminSite

SECTION_ORDER: tuple[str, ...] = (
    'Logs / Operations',
    'Security',
    'Core Platform',
    'Scheduling',
    'App Modules',
    'Learning Apps',
    'Other',
)

APP_SECTIONS: dict[str, str] = {
    'axes': 'Security',
    'django_celery_beat': 'Scheduling',
    'otp_totp': 'Security',
    'otp_static': 'Security',
    'accounts': 'Core Platform',
    'cohorts': 'Core Platform',
    'feedback': 'Core Platform',
    'google_storage': 'Core Platform',
    'powerhub_config': 'App Modules',
    'workflows': 'Learning Apps',
    'tasks': 'Learning Apps',
    'goals': 'Learning Apps',
    'habits': 'Learning Apps',
    'reflections': 'Learning Apps',
    'journal': 'Learning Apps',
    'group_space': 'Learning Apps',
    'resources': 'Learning Apps',
    'bug_reports': 'Learning Apps',
}

# Fine-grained overrides for models that should appear in a different section
# than their Django app.
MODEL_SECTION_OVERRIDES: dict[str, str] = {
    'accounts.auditlog': 'Logs / Operations',
}

# App labels in display order (logs → core → toggles → learning apps).
ADMIN_APP_ORDER: tuple[str, ...] = (
    'axes',
    'django_celery_beat',
    'otp_totp',
    'otp_static',
    'accounts',
    'cohorts',
    'feedback',
    'google_storage',
    'powerhub_config',
    'workflows',
    'tasks',
    'goals',
    'habits',
    'reflections',
    'journal',
    'group_space',
    'resources',
    'bug_reports',
)


class PowerHubAdminSite(AdminSite):
    site_header = 'PowerHUB Administration'
    site_title = 'PowerHUB Admin'
    index_title = 'Site administration'
    index_template = 'admin/powerhub_index.html'

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        order = {label: index for index, label in enumerate(ADMIN_APP_ORDER)}
        section_order = {label: index for index, label in enumerate(SECTION_ORDER)}
        for app in app_list:
            section = APP_SECTIONS.get(app['app_label'], 'Other')
            app['powerhub_section'] = section
        app_list.sort(
            key=lambda app: (
                section_order.get(app['powerhub_section'], len(SECTION_ORDER)),
                order.get(app['app_label'], len(ADMIN_APP_ORDER)),
                app['name'].lower(),
            )
        )
        return app_list

    def each_context(self, request):
        context = super().each_context(request)
        app_list = self.get_app_list(request)
        app_order = {label: index for index, label in enumerate(ADMIN_APP_ORDER)}
        grouped: dict[str, list[dict]] = {section: [] for section in SECTION_ORDER}
        split_apps: dict[tuple[str, str], dict] = {}

        for app in app_list:
            app_label = app['app_label']
            default_section = app.get('powerhub_section', 'Other')
            for model in app.get('models', []):
                model_key = f"{app_label}.{model.get('object_name', '').lower()}"
                section = MODEL_SECTION_OVERRIDES.get(model_key, default_section)
                split_key = (section, app_label)
                if split_key not in split_apps:
                    split_apps[split_key] = {
                        'name': app['name'],
                        'app_label': app_label,
                        'app_url': app['app_url'],
                        'has_module_perms': app['has_module_perms'],
                        'models': [],
                    }
                split_apps[split_key]['models'].append(model)

        for (section, _), app in sorted(
            split_apps.items(),
            key=lambda item: (
                app_order.get(item[0][1], len(ADMIN_APP_ORDER)),
                item[1]['name'].lower(),
            ),
        ):
            grouped.setdefault(section, []).append(app)

        context['powerhub_sections'] = [
            {'title': section, 'apps': grouped.get(section, [])}
            for section in SECTION_ORDER
        ]
        return context


def install_powerhub_admin_site() -> None:
    """Replace default admin.site after all ModelAdmins are registered."""
    from django.contrib import admin

    if isinstance(admin.site, PowerHubAdminSite):
        return

    custom_site = PowerHubAdminSite(name='admin')
    custom_site._registry = admin.site._registry.copy()
    admin.site = custom_site

    import django.contrib.admin.sites

    django.contrib.admin.sites.site = custom_site
