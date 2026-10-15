# Community Feature Removal Audit

This audit catalogs every file containing references to the Community feature (reposts, feed, community comments, criticality escalation, affected counts, similar issues, moderation) and determines the exact action to be taken in accordance with the specification.

| Item / Matched Terms | File | Action | Details |
| --- | --- | --- | --- |
| community, repost | DEMO_CREDENTIALS.md | **repoint** | Update documentation to reflect removal of Community feature and release notes |
| community, criticality, moderate_comment, repost | README.md | **repoint** | Update documentation to reflect removal of Community feature and release notes |
| criticality | apps\announcements\migrations\0001_initial.py | **keep deprecated** | Historical migration files containing schema definitions |
| visibility | apps\announcements\views.py | **repoint** | Inspect and clean up community references |
| community | apps\core\mixins.py | **repoint** | Inspect and clean up community references |
| community | apps\core\navigation.py | **repoint** | Inspect and clean up community references |
| community, criticality, repost, visibility | apps\core\permissions.py | **repoint** | Inspect and clean up community references |
| community, repost | apps\dashboard\selectors.py | **repoint** | Inspect and clean up community references |
| affected_count, community, repost, trending, visibility | apps\dashboard\views.py | **repoint** | Inspect and clean up community references |
| community, repost | apps\notifications\models.py | **repoint** | Inspect and clean up community references |
| base_priority, community, criticality, repost, visibility | apps\tickets\admin.py | **repoint** | Inspect and clean up community references |
| community, similar | apps\tickets\community_urls.py | **repoint** | Inspect and clean up community references |
| affected_count, community, repost, similar, visibility | apps\tickets\community_views.py | **repoint** | Inspect and clean up community references |
| base_priority, community, criticality, repost, visibility | apps\tickets\factories.py | **repoint** | Inspect and clean up community references |
| base_priority, community, criticality, repost, show_reporter_name, similar, visibility | apps\tickets\forms.py | **repoint** | Inspect and clean up community references |
| criticality, repost | apps\tickets\management\commands\clear_demo_data.py | **repoint** | Remove community tickets, reposts, comments from seed data |
| community | apps\tickets\management\commands\moderate_comment.py | **repoint** | Inspect and clean up community references |
| base_priority, community, criticality, repost, show_reporter_name, visibility | apps\tickets\management\commands\seed_demo_data.py | **repoint** | Inspect and clean up community references |
| community | apps\tickets\migrations\0004_category_allow_community.py | **keep deprecated** | Historical migration files containing schema definitions |
| base_priority, community, repost, show_reporter_name, visibility | apps\tickets\migrations\0005_ticket_community_fields.py | **keep deprecated** | Historical migration files containing schema definitions |
| community, repost | apps\tickets\migrations\0006_ticketrepost.py | **keep deprecated** | Historical migration files containing schema definitions |
| community, repost | apps\tickets\migrations\0007_ticketcomment_scope.py | **keep deprecated** | Historical migration files containing schema definitions |
| criticality, repost | apps\tickets\migrations\0008_criticalityrule_and_seeds.py | **keep deprecated** | Historical migration files containing schema definitions |
| community, criticality, repost, visibility | apps\tickets\migrations\0009_rename_tickets_tic_hostel__e6d3bf_idx_tickets_tic_hostel__927531_idx_and_more.py | **keep deprecated** | Historical migration files containing schema definitions |
| community, repost, visibility | apps\tickets\migrations\0010_ticket_delete_reason_ticket_deleted_at_and_more.py | **keep deprecated** | Historical migration files containing schema definitions |
| affected_count, base_priority, community, criticality, repost, show_reporter_name, visibility | apps\tickets\models.py | **repoint** | Inspect and clean up community references |
| community, visibility | apps\tickets\querysets.py | **repoint** | Inspect and clean up community references |
| affected_count, community, criticality, repost, similar, trending, visibility | apps\tickets\services\community.py | **repoint** | Inspect and clean up community references |
| affected_count, base_priority, criticality, repost | apps\tickets\services\criticality.py | **repoint** | Inspect and clean up community references |
| repost | apps\tickets\services\deletion.py | **repoint** | Inspect and clean up community references |
| community, criticality, repost | apps\tickets\urls.py | **repoint** | Inspect and clean up community references |
| criticality | apps\tickets\views\__init__.py | **repoint** | Inspect and clean up community references |
| affected_count, community, repost, visibility | apps\tickets\views\detail.py | **repoint** | Inspect and clean up community references |
| criticality, repost | apps\tickets\views\manage.py | **repoint** | Inspect and clean up community references |
| community, criticality, repost | apps\tickets\views\settings.py | **repoint** | Inspect and clean up community references |
| affected_count, similar | config\settings\base.py | **repoint** | Inspect and clean up community references |
| community | config\urls.py | **repoint** | Inspect and clean up community references |
| community | docs\permission-audit.md | **repoint** | Inspect and clean up community references |
| community, criticality, moderate_comment, repost | docs\release-notes.md | **repoint** | Inspect and clean up community references |
| community, criticality | docs\removal-audit.md | **repoint** | Inspect and clean up community references |
| community, criticality, repost | docs\repo-state.md | **repoint** | Inspect and clean up community references |
| community, criticality, repost, similar | docs\routes-before.txt | **repoint** | Inspect and clean up community references |
| affected_count, community, criticality, moderate_comment, repost, similar | plan\ACCESS_CLEANUP_AND_STAFF_MANAGEMENT_PLAN.md | **repoint** | Inspect and clean up community references |
| affected_count, base_priority, community, crit-, criticality, post_card, repost, show_reporter_name, similar, trending, visibility | plan\COMMUNITY_FEED_AND_ANNOUNCEMENTS_PLAN.md | **repoint** | Inspect and clean up community references |
| community, crit-, criticality, repost, similar | plan\DELETE_DARKMODE_MOBILE_RESIDENCE_PLAN.md | **repoint** | Inspect and clean up community references |
| community, repost | plan\HOSTEL_STRUCTURE_AND_REGISTRATION_PLAN.md | **repoint** | Inspect and clean up community references |
| similar | plan\HOSTEL_TICKET_SYSTEM_PLAN.md | **repoint** | Inspect and clean up community references |
| community, crit-, criticality, repost | static\css\components.css | **repoint** | Inspect and clean up community references |
| visibility | static\css\layout.css | **repoint** | Inspect and clean up community references |
| community, crit-, criticality, visibility | static\css\tokens.css | **repoint** | Inspect and clean up community references |
| visibility | static\vendor\alpine.min.js | **repoint** | Inspect and clean up community references |
| visibility | static\vendor\chart.min.js | **repoint** | Inspect and clean up community references |
| trending | static\vendor\lucide.min.js | **repoint** | Inspect and clean up community references |
| visibility | templates\accounts\login.html | **repoint** | Inspect and clean up community references |
| crit- | templates\announcements\detail.html | **repoint** | Inspect and clean up community references |
| crit- | templates\announcements\list.html | **repoint** | Inspect and clean up community references |
| crit- | templates\announcements\manage_list.html | **repoint** | Inspect and clean up community references |
| affected_count, base_priority, community, crit-, repost | templates\community\_card_footer.html | **repoint** | Inspect and clean up community references |
| community | templates\community\_comment_thread.html | **repoint** | Inspect and clean up community references |
| community, post_card, repost | templates\community\_feed_list.html | **repoint** | Inspect and clean up community references |
| affected_count, base_priority, community, crit-, criticality, repost, show_reporter_name | templates\community\_post_card.html | **repoint** | Inspect and clean up community references |
| repost, similar | templates\community\_similar_tickets.html | **repoint** | Inspect and clean up community references |
| community, repost, trending | templates\community\feed.html | **repoint** | Inspect and clean up community references |
| community, repost, trending | templates\dashboard\hosteler.html | **repoint** | Inspect and clean up community references |
| community, crit-, repost | templates\dashboard\staff.html | **repoint** | Inspect and clean up community references |
| affected_count, repost | templates\tickets\_kanban_card.html | **repoint** | Inspect and clean up community references |
| affected_count, base_priority, repost, trending | templates\tickets\_list_table.html | **repoint** | Inspect and clean up community references |
| community, repost, show_reporter_name, similar | templates\tickets\create.html | **repoint** | Inspect and clean up community references |
| affected_count, base_priority, community, crit-, repost, visibility | templates\tickets\detail.html | **repoint** | Inspect and clean up community references |
| repost | templates\tickets\list.html | **repoint** | Inspect and clean up community references |
| community, criticality, repost | templates\tickets\manage_criticality.html | **repoint** | Inspect and clean up community references |
| community, criticality, repost, trending | templates\tickets\manage_settings.html | **repoint** | Inspect and clean up community references |
| community, criticality, repost, visibility | tests\test_access_cleanup.py | **repoint** | Inspect and clean up community references |
| affected_count, base_priority, community, criticality, repost, similar, visibility | tests\test_community_and_announcements_services.py | **repoint** | Inspect and clean up community references |
| base_priority, community, criticality, repost, show_reporter_name, similar, visibility | tests\test_community_and_announcements_views.py | **repoint** | Inspect and clean up community references |
| repost, visibility | tests\test_deletion.py | **repoint** | Inspect and clean up community references |
| community | tests\test_mobile.py | **repoint** | Inspect and clean up community references |
| community, repost, visibility | tests\test_registration.py | **repoint** | Inspect and clean up community references |
