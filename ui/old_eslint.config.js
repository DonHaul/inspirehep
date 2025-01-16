import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import babelParser from "@babel/eslint-parser";
import typescriptEslint from "@typescript-eslint/eslint-plugin";
import { FlatCompat } from "@eslint/eslintrc";
import tsParser from "@typescript-eslint/parser";
import path from "node:path";
import { fileURLToPath } from "node:url";
import eslintPluginReact from 'eslint-plugin-react';
import eslintPluginPrettierRecommended  from 'eslint-plugin-prettier/recommended';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import importPlugin from 'eslint-plugin-import';
import js from "@eslint/js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({
    baseDirectory: __dirname
});

export default [
    {ignores: ['node_modules/**']},
    js.configs.recommended,
    //eslintPluginPrettierRecommended,
    importPlugin.flatConfigs.recommended,
    ...compat.extends("airbnb").map(config => ({
        ...config,
        files: ["**/*.{js,jsx,ts,tsx}"],
    })),

{
    files: ["**/*.{js,jsx,ts,tsx}"],
    plugins: {
        "react-hooks": reactHooks,
        'jsx-a11y': jsxA11y,
        "react":eslintPluginReact,
    },

    languageOptions: {
        globals: {
            ...globals.browser,
            ...globals.jest,
        },

        parser: babelParser,
    },

    settings: {
        "import/resolver": {
            node: {
                extensions: [".js", ".jsx", ".ts", ".tsx"],
            },
        },
    },

    rules: {
        "func-names": "off",
        "no-plusplus": "off",
        "no-param-reassign": ["error", {
            props: false,
        }],

        "no-underscore-dangle": ["error", {
            allow: ["_source", "_id"],
        }],

        "jsx-a11y/anchor-is-valid": ["error", {
            components: ["Link"],
            specialLink: ["to", "hrefLeft", "hrefRight"],
            aspects: ["noHref", "invalidHref", "preferButton"],
        }],

        "import/no-extraneous-dependencies": ["off", {
            devDependencies: ["**/*.test.jsx?"],
        }],

        "import/prefer-default-export": "off",

        "import/extensions": ["error", "ignorePackages", {
            js: "never",
            jsx: "never",
            ts: "never",
            tsx: "never",
        }],

        "react/no-unused-prop-types": "off",
        "react/require-default-props": "off",
        "react/prop-types": "off",
        "react/forbid-prop-types": "off",
        "react-hooks/exhaustive-deps": "warn",
        "react/destructuring-assignment": "off",
        "react/prefer-stateless-function": "off",
        "react-hooks/rules-of-hooks": "error",
        "react/jsx-no-target-blank": "off",

        "react/jsx-filename-extension": [2, {
            extensions: [".js", ".jsx", ".ts", ".tsx"],
        }],

        "jsx-a11y/no-static-element-interactions": "off",
        "jsx-a11y/click-events-have-key-events": "off",
    },
}, {
    files: ["src/middlewares/*.js"],

    rules: {
        "arrow-body-style": "off",
    },
}, {
    files: ["**/*.ts", "**/*.tsx"],

    plugins: {
        "@typescript-eslint": typescriptEslint,
    },

    languageOptions: {
        parser: tsParser,
    },
    rules: {
        "no-nested-ternary": "off",
        "no-undef": "off",
        "no-unused-vars": "off",
        "no-use-before-define": "off",
        camelcase: "off",
        "react/default-props-match-prop-types": "off",
        "no-shadow": "off",
        "arrow-body-style": "off",
        "react/jsx-no-bind": "off",
        "react/jsx-no-target-blank": "off",
        "import/no-cycle": "off",
    },
},
{
        files: ['**/__tests__/**/*'],
        rules: {
          'no-import-assign': 'off',
        },
}
];
