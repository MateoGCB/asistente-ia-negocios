// Backend limits replicated in the forms. The backend is still the authority: these only help
// the user before sending. Values copied from the backend schemas (written down on purpose).

export const USER_NAME_MAX = 100;
export const PASSWORD_MIN_CHARS = 8;
export const PASSWORD_MAX_BYTES = 72; // bcrypt limit: counted in UTF-8 BYTES, not characters

export const BUSINESS_NAME_MAX = 100;
export const INDUSTRY_MAX = 60;
export const PICKUP_HOURS_MIN = 1;
export const PICKUP_HOURS_MAX = 72;
export const PICKUP_HOURS_DEFAULT = 24;

export const MENU_NAME_MAX = 100;
export const ITEM_NAME_MAX = 100;
export const ITEM_DESCRIPTION_MAX = 500;
export const ITEM_PRICE_MAX_CENTS = 9_999_999_999; // Numeric(10, 2): 99.999.999,99

export const ORDER_QTY_MIN = 1;
export const ORDER_QTY_MAX = 50; // per item
export const ORDER_ITEMS_MAX = 30; // different items per order
export const ORDER_TOTAL_MAX_CENTS = 1_000_000_000; // $ 10.000.000
export const CUSTOMER_NAME_MIN = 2;
export const CUSTOMER_NAME_MAX = 100;
export const PHONE_MIN_DIGITS = 6;
export const PHONE_MAX_DIGITS = 15;
export const PHONE_MAX_LENGTH = 20;
export const NOTES_MAX = 300;

export const HISTORY_PAGE_SIZE = 20;
export const ACTIVE_REFRESH_MS = 15_000;
