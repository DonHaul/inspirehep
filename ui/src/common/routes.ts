import { getConfigFor } from './config';

export const HOME = '/';

export const LITERATURE = '/literature';

export const AUTHORS = '/authors';

export const JOBS = '/jobs';

export const CONFERENCES = '/conferences';

export const INSTITUTIONS = '/institutions';

export const SEMINARS = '/seminars';

export const EXPERIMENTS = '/experiments';

export const JOURNALS = '/journals';

export const DATA = '/data';

export const USER = '/user';
export const USER_PROFILE = `${USER}/profile`;
export const USER_LOGIN = `${USER}/login`;
export const USER_SIGNUP = `${USER}/signup`;
export const USER_LOCAL_LOGIN = `${USER_LOGIN}/local`;
export const USER_SETTINGS = `${USER}/settings`;

export const HOLDINGPEN = '/holdingpen';
export const HOLDINGPEN_DASHBOARD = `${HOLDINGPEN}/dashboard`;
export const HOLDINGPEN_INSPECT = `${HOLDINGPEN}/inspect`;

export const BACKOFFICE = '/backoffice';
export const BACKOFFICE_LOGIN = `${BACKOFFICE}/login`;
export const BACKOFFICE_LOCAL_LOGIN = `${BACKOFFICE_LOGIN}/local`;
export const BACKOFFICE_SEARCH = `${BACKOFFICE}/search`;
export const BACKOFFICE_BACKEND = getConfigFor('BACKOFFICE_URL');
export const BACKOFFICE_API = `${BACKOFFICE_BACKEND}/api`;
export const BACKOFFICE_LOGIN_ORCID = `${BACKOFFICE_BACKEND}/accounts/orcid/login/`;
export const BACKOFFICE_LOGIN_API = `${BACKOFFICE_API}/token/`;
export const BACKOFFICE_SEARCH_API = `${BACKOFFICE_API}/workflows/authors/search`;

export const ERRORS = '/errors';
export const ERROR_401 = `${ERRORS}/401`;
export const ERROR_404 = `${ERRORS}/404`;
export const ERROR_500 = `${ERRORS}/500`;
export const ERROR_NETWORK = `${ERRORS}/network`;

export const SUBMISSIONS = '/submissions';
export const SUBMISSIONS_AUTHOR = `${SUBMISSIONS}/authors`;
export const SUBMISSIONS_LITERATURE = `${SUBMISSIONS}/literature`;
export const SUBMISSIONS_JOB = `${SUBMISSIONS}/jobs`;
export const SUBMISSIONS_CONFERENCE = `${SUBMISSIONS}/conferences`;
export const SUBMISSIONS_SEMINAR = `${SUBMISSIONS}/seminars`;
export const SUBMISSIONS_INSTITUTION = `${SUBMISSIONS}/institutions`;
export const SUBMISSIONS_EXPERIMENT = `${SUBMISSIONS}/experiments`;
export const SUBMISSIONS_JOURNAL = `${SUBMISSIONS}/journals`;
export const SUBMISSION_SUCCESS = `${SUBMISSIONS}/success`;

export const EDIT_LITERATURE = '/editor/record/literature';
export const EDIT_AUTHOR = SUBMISSIONS_AUTHOR;
export const EDIT_AUTHOR_CATALOGER = '/editor/record/authors';
export const EDIT_JOB = SUBMISSIONS_JOB;
export const EDIT_CONFERENCE = '/editor/record/conferences';
export const EDIT_INSTITUTION = '/editor/record/institutions';
export const EDIT_JOURNAL = '/editor/record/journals';
export const EDIT_EXPERIMENT = '/editor/record/experiments';
export const EDIT_DATA = '/editor/record/data';
export const EDIT_SEMINAR = SUBMISSIONS_SEMINAR;

export const BIBLIOGRAPHY_GENERATOR = '/bibliography-generator';
