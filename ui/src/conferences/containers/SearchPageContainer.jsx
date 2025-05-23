import React, { useCallback } from 'react';
import PropTypes from 'prop-types';
import { Row, Col } from 'antd';
import { connect } from 'react-redux';

import AggregationFiltersContainer from '../../common/containers/AggregationFiltersContainer';
import PaginationContainer from '../../common/containers/PaginationContainer';
import SortByContainer from '../../common/containers/SortByContainer';
import ResultsContainer from '../../common/containers/ResultsContainer';
import NumberOfResultsContainer from '../../common/containers/NumberOfResultsContainer';
import LoadingOrChildren from '../../common/components/LoadingOrChildren';
import ResponsiveView from '../../common/components/ResponsiveView';
import DrawerHandle from '../../common/components/DrawerHandle';
import DocumentHead from '../../common/components/DocumentHead';
import { CONFERENCES_NS } from '../../search/constants';
import ConferenceItem from '../components/ConferenceItem';
import ConferenceStartDateFilterContainer from './ConferenceStartDateFilterContainer';
import {
  SEARCH_PAGE_GUTTER,
  SEARCH_PAGE_COL_SIZE_WITH_FACETS,
} from '../../common/constants';
import { APIButton } from '../../common/components/APIButton';
import { isSuperUser } from '../../common/authorization';
import EmptyOrChildren from '../../common/components/EmptyOrChildren';

const META_DESCRIPTION = 'Find conferences in High Energy Physics';
const TITLE = 'Conferences Search';

function renderConferenceItem(result) {
  return <ConferenceItem metadata={result.get('metadata')} />;
}

function ConferenceSearchPage({
  loading,
  loadingAggregations,
  isSuperUserLoggedIn,
  results,
}) {
  const renderAggregations = useCallback(
    () => (
      <>
        <ConferenceStartDateFilterContainer switchTitle="Upcoming conferences" />
        <LoadingOrChildren loading={loadingAggregations}>
          <AggregationFiltersContainer
            namespace={CONFERENCES_NS}
            page="Conferences search"
          />
        </LoadingOrChildren>
      </>
    ),
    [loadingAggregations]
  );

  return (
    <>
      <DocumentHead title={TITLE} description={META_DESCRIPTION} />
      <Row>
        <Col {...SEARCH_PAGE_COL_SIZE_WITH_FACETS}>
          <Row
            className="mt3"
            gutter={SEARCH_PAGE_GUTTER}
            type="flex"
            justify="start"
          >
            <Col xs={0} lg={7}>
              <ResponsiveView min="lg" render={renderAggregations} />
            </Col>
            <Col xs={24} lg={17}>
              <EmptyOrChildren data={results} title="0 Conferences">
                <LoadingOrChildren loading={loading}>
                  <Row type="flex" align="middle" justify="end">
                    <Col xs={24} lg={12}>
                      <NumberOfResultsContainer namespace={CONFERENCES_NS} />
                      {isSuperUserLoggedIn && (
                        <APIButton url={window.location.href} />
                      )}
                    </Col>
                    <Col xs={12} lg={0}>
                      <ResponsiveView
                        max="md"
                        render={() => (
                          <DrawerHandle
                            className="mt2"
                            handleText="Filter"
                            drawerTitle="Filter"
                          >
                            {renderAggregations()}
                          </DrawerHandle>
                        )}
                      />
                    </Col>
                    <Col className="tr" span={12}>
                      <SortByContainer namespace={CONFERENCES_NS} />
                    </Col>
                  </Row>
                  <Row>
                    <Col span={24}>
                      <ResultsContainer
                        namespace={CONFERENCES_NS}
                        renderItem={renderConferenceItem}
                      />
                      <PaginationContainer namespace={CONFERENCES_NS} />
                    </Col>
                  </Row>
                </LoadingOrChildren>
              </EmptyOrChildren>
            </Col>
          </Row>
        </Col>
      </Row>
    </>
  );
}

ConferenceSearchPage.propTypes = {
  loading: PropTypes.bool.isRequired,
  loadingAggregations: PropTypes.bool.isRequired,
};

const stateToProps = (state) => ({
  isSuperUserLoggedIn: isSuperUser(state.user.getIn(['data', 'roles'])),
  loading: state.search.getIn(['namespaces', CONFERENCES_NS, 'loading']),
  loadingAggregations: state.search.getIn([
    'namespaces',
    CONFERENCES_NS,
    'loadingAggregations',
  ]),
  results: state.search.getIn(['namespaces', CONFERENCES_NS, 'results']),
});

export default connect(stateToProps)(ConferenceSearchPage);
