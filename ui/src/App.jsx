import React, { useEffect } from 'react';
import { Route } from 'react-router-dom';
import { connect } from 'react-redux';
import { Layout } from 'antd';
import Loadable from 'react-loadable';
import PropTypes from 'prop-types';
import { List } from 'immutable';

import './App.less';
import Header from './common/layouts/Header';
import Footer from './common/layouts/Footer';
import Loading from './common/components/Loading';
import SafeSwitch from './common/components/SafeSwitch';
import PrivateRoute from './common/PrivateRoute';

import {
  HOME,
  USER,
  HOLDINGPEN,
  BACKOFFICE,
  LITERATURE,
  AUTHORS,
  SUBMISSIONS,
  ERRORS,
  JOBS,
  CONFERENCES,
  INSTITUTIONS,
  SEMINARS,
  DATA,
  EXPERIMENTS,
  BIBLIOGRAPHY_GENERATOR,
  JOURNALS,
} from './common/routes';
import { setUserCategoryFromRoles, setClientId } from './tracker';
import { fetchLoggedInUser } from './actions/user';
import Home from './home';
import Literature from './literature';
import Conferences from './conferences';
import Data from './data';
import Authors from './authors';
import Jobs from './jobs';
import User from './user';
import Errors from './errors';
import GuideModalContainer from './common/containers/GuideModalContainer';
import { changeGuideModalVisibility } from './actions/ui';
import { getConfigFor } from './common/config';
import Institutions from './institutions';
import Seminars from './seminars';
import Experiments from './experiments';
import Journals from './journals';
import BibliographyGeneratorPageContainer from './bibliographyGenerator/BibliographyGeneratorPageContainer';
import { SUPERUSER_OR_CATALOGER } from './common/authorization';

const Holdingpen$ = Loadable({
  loader: () => import('./holdingpen'),
  loading: Loading,
});
const Backoffice$ = Loadable({
  loader: () => import('./backoffice'),
  loading: Loading,
});
const Submissions$ = Loadable({
  loader: () => import('./submissions'),
  loading: Loading,
});

function App({ userRoles, dispatch, guideModalVisibility }) {
  useEffect(() => {
    dispatch(fetchLoggedInUser());
  }, [dispatch]);

  useEffect(() => {
    const hasGuideModalBeenDisplayed = guideModalVisibility != null;
    const shouldDisplayGuideOnStart = getConfigFor('DISPLAY_GUIDE_ON_START');
    if (!hasGuideModalBeenDisplayed && shouldDisplayGuideOnStart) {
      setTimeout(() => {
        dispatch(changeGuideModalVisibility(true));
      }, 3000);
    }
  }, [guideModalVisibility, dispatch]);

  useEffect(() => {
    setUserCategoryFromRoles(userRoles);
  }, [userRoles]);

  useEffect(() => {
    setClientId();
  }, []);

  return (
    <Layout className="__App__" data-testid="app">
      <Header />
      <Layout.Content className="content">
        <SafeSwitch id="main">
          <Route exact path={HOME} component={Home} />
          <Route path={USER} component={User} />
          <PrivateRoute path={HOLDINGPEN} component={Holdingpen$} />
          <PrivateRoute
            path={BACKOFFICE}
            component={Backoffice$}
            authorizedRoles={SUPERUSER_OR_CATALOGER}
          />
          <Route path={LITERATURE} component={Literature} />
          <Route path={AUTHORS} component={Authors} />
          <Route path={JOBS} component={Jobs} />
          <Route path={CONFERENCES} component={Conferences} />
          <Route path={INSTITUTIONS} component={Institutions} />
          <Route path={SEMINARS} component={Seminars} />
          <Route path={EXPERIMENTS} component={Experiments} />
          <Route path={JOURNALS} component={Journals} />
          <Route path={DATA} component={Data} />
          <PrivateRoute path={SUBMISSIONS} component={Submissions$} />
          <Route
            path={BIBLIOGRAPHY_GENERATOR}
            component={BibliographyGeneratorPageContainer}
          />
          <Route path={ERRORS} component={Errors} />
        </SafeSwitch>
        <GuideModalContainer />
      </Layout.Content>
      <Footer />
    </Layout>
  );
}

App.propTypes = {
  guideModalVisibility: PropTypes.bool,
  userRoles: PropTypes.instanceOf(List).isRequired,
  dispatch: PropTypes.func.isRequired,
};

const stateToProps = (state) => ({
  guideModalVisibility: state.ui.get('guideModalVisibility'),
  userRoles: state.user.getIn(['data', 'roles']),
});

const dispatchToProps = (dispatch) => ({
  dispatch,
});

export default connect(stateToProps, dispatchToProps)(App);
