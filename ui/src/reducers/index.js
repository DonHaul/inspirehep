import { combineReducers } from 'redux';
import { connectRouter } from 'connected-react-router';

import search, { initialState as searchInitialState } from './search';
import literature from './literature';
import exceptions from './exceptions';
import inspect from './inspect';
import user, { initialState as userInitialState } from './user';
import submissions from './submissions';
import citations from './citations';
import authors from './authors';
import jobs from './jobs';
import conferences from './conferences';
import institutions from './institutions';
import data from './data';
import seminars from './seminars';
import experiments from './experiments';
import journals from './journals';
import bibliographyGenerator from './bibliographyGenerator';
import settings from './settings';
import ui, { initialState as uiInitialState } from './ui';
import backoffice, {
  initialState as backofficeInitialState,
} from './backoffice';
import { LITERATURE_NS, LITERATURE_REFERENCES_NS } from '../search/constants';

export default function createRootReducer(history) {
  return combineReducers({
    router: connectRouter(history),
    exceptions,
    inspect,
    literature,
    user,
    settings,
    search,
    submissions,
    citations,
    authors,
    ui,
    jobs,
    conferences,
    institutions,
    seminars,
    experiments,
    data,
    bibliographyGenerator,
    journals,
    backoffice,
  });
}

export const REDUCERS_TO_PERSISTS = [
  { name: 'ui', initialState: uiInitialState },
  { name: 'user', initialState: userInitialState },
  {
    name: 'search',
    initialState: searchInitialState,
    statePath: ['namespaces', LITERATURE_REFERENCES_NS, 'query', 'size'],
  },
  {
    name: 'search',
    initialState: searchInitialState,
    statePath: ['namespaces', LITERATURE_NS, 'query', 'size'],
  },
  { name: 'backoffice', initialState: backofficeInitialState },
];
