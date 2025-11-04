# 📋 Información sobre Migraciones

## ✅ Migraciones Activas (en build.sh)

Estas migraciones se ejecutan automáticamente en cada deploy y son **seguras** (solo agregan columnas/tablas, NO borran datos):

1. **migrate_add_original_order_id.py** - Agrega columna `original_order_id` a `charges`
2. **migrate_add_users_and_vendors.py** - Crea tabla `users` y agrega `vendor_id` a `customers` y `orders`
3. **migrate_add_vendor_system.py** - Crea tabla `users` y agrega `vendor_id` (puede estar duplicado con la anterior)
4. **migrate_add_weekly_offer_dates.py** - Agrega columnas `start_date` y `end_date` a `weekly_offers` (SEGURA)
5. **migrate_add_social_tables.py** - Crea tablas de social media (SEGURA)

## 🗄️ Migraciones Archivadas

Estas migraciones NO se ejecutan automáticamente y están en `migrations_archived/`:

1. **migrate_update_weekly_offers_product_id.py** - ⚠️ **PELIGROSA**: Borraba ofertas. Ya no se ejecuta automáticamente.
2. **migrate_add_weekly_offers.py** - Ya no necesaria (la tabla se crea con `db.create_all()`)

## ⚠️ Importante

- **NUNCA** ejecutar `migrate_update_weekly_offers_product_id.py` en producción sin revisar primero
- Todas las migraciones activas son idempotentes (se pueden ejecutar múltiples veces sin problemas)
- Las migraciones solo agregan estructura, NO borran datos

