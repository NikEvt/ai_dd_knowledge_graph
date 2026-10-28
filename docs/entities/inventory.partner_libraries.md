<!-- Сгенерировано tools/knowledge/render_docs.py. Не править руками: правьте модель и перегенерируйте. -->

# inventory.partner_libraries
Миграция: `inventory.partner_libraries`

## Поля
- id: integer NOT NULL PK
- code: text NOT NULL
- name: text NOT NULL
- daily_penalty: numeric NOT NULL
- max_active_loans: integer NOT NULL
- suspended: boolean NOT NULL

## Связи (FK)
- inventory.ill_loans.partner_id → сюда
- inventory.ill_penalties.partner_id → сюда

## Ограничения и триггеры
- partner_libraries_code_check (check на inventory.partner_libraries): CHECK ((code ~ '^[A-Z0-9-]{2,16}$'::text))
- partner_libraries_daily_penalty_check (check на inventory.partner_libraries): CHECK ((daily_penalty >= (0)::numeric))
- partner_libraries_max_active_loans_check (check на inventory.partner_libraries): CHECK ((max_active_loans > 0))
- partner_libraries_code_key (unique на inventory.partner_libraries): UNIQUE (code)

## ORM
- services/inventory/models.py::PartnerLibrary:26 (orm_model)

## Пишут (код)
- services/inventory/service.py::register_partner
- services/inventory/service.py::review_partner_debt [suspended]
- services/inventory/service.py::settle_penalty [suspended]

## Правила
- R-INVENTORY-ILL-02 Партнёр без новых выдач при приостановке, просрочке, лимите или долге (подкреплено кодом и тестами)
- R-INVENTORY-PARTNER-01 Код библиотеки-партнёра уникален и имеет формат A-Z0-9- (⚠ без тестов)
- R-INVENTORY-PARTNER-02 Партнёр приостанавливается, когда долг по пеням превышает лимит (подкреплено кодом и тестами)
- R-INVENTORY-PARTNER-03 Оплата пеней возобновляет выдачи, когда долг опускается до лимита (подкреплено кодом и тестами)
- R-INVENTORY-PENALTY-04 Пени за просрочку — дневная ставка партнёра × дни, не более ILL_PENALTY_MAX_DAYS (подкреплено кодом и тестами)
- R-INVENTORY-PENALTY-07 Оплатить можно только итоговые пени (подкреплено кодом и тестами)
