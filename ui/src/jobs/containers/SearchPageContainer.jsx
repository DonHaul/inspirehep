import React, { Component } from 'react';
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
import JobItem from '../components/JobItem';
import SubscribeJobsModalButton from '../components/SubscribeJobsModalButton';
import DocumentHead from '../../common/components/DocumentHead';
import { JOBS_NS } from '../../search/constants';
import { APIButton } from '../../common/components/APIButton';
import { isSuperUser } from '../../common/authorization';
import { columnSize } from '../../common/utils';
import EmptyOrChildren from '../../common/components/EmptyOrChildren';

const META_DESCRIPTION =
  'Jobs in High-Energy Physics. A listing of academic and research jobs of interest to the community in high energy physics, nuclear physics, accelerator physics and astrophysics.';
const TITLE = 'Jobs Search';

class SearchPage extends Component {
  static renderJobResultItem(result) {
    return (
      <JobItem
        metadata={result.get('metadata')}
        created={result.get('created')}
      />
    );
  }

  static renderSubscribeJobsModalButton() {
    return <SubscribeJobsModalButton />;
  }

  constructor(props) {
    super(props);
    this.renderAggregationsDrawer = this.renderAggregationsDrawer.bind(this);
    this.renderAggregations = this.renderAggregations.bind(this);
  }

  renderAggregations() {
    const { loadingAggregations } = this.props;
    return (
      <div className="mt3">
        <LoadingOrChildren loading={loadingAggregations}>
          <Row type="flex" justify="space-between">
            <Col className="f5">Select Job Filters:</Col>
            <Col>{SearchPage.renderSubscribeJobsModalButton()}</Col>
          </Row>
          <AggregationFiltersContainer
            inline
            displayWhenNoResults
            namespace={JOBS_NS}
            page="Jobs search"
          />
        </LoadingOrChildren>
      </div>
    );
  }

  renderAggregationsDrawer() {
    const { loadingAggregations } = this.props;
    return (
      <DrawerHandle className="mt2" handleText="Filter" drawerTitle="Filter">
        <LoadingOrChildren loading={loadingAggregations}>
          <AggregationFiltersContainer
            inline
            displayWhenNoResults
            namespace={JOBS_NS}
            page="Jobs search"
          />
        </LoadingOrChildren>
      </DrawerHandle>
    );
  }

  // TODO: investigate if it is better to use `Context` to pass namespace rather than props
  render() {
    const { loading, isSuperUserLoggedIn, results, numberOfResults } =
      this.props;
    return (
      <>
        <DocumentHead title={TITLE} description={META_DESCRIPTION} />
        <div>
          <Row className="bg-white mb3" type="flex" justify="center">
            <Col xs={0} lg={16} xl={16} xxl={14}>
              <ResponsiveView min="lg" render={this.renderAggregations} />
            </Col>
          </Row>
          <Row
            type="flex"
            justify="center"
            data-testid="jobs-search-page-container"
          >
            <Col {...columnSize(numberOfResults)}>
              <EmptyOrChildren data={results} title="0 Jobs">
                <LoadingOrChildren loading={loading}>
                  <Row type="flex" align="middle" justify="end">
                    <Col xs={12} lg={12}>
                      <NumberOfResultsContainer namespace={JOBS_NS} />
                      {isSuperUserLoggedIn && (
                        <APIButton url={window.location.href} />
                      )}
                    </Col>
                    <Col className="tr" xs={12} lg={0}>
                      <ResponsiveView
                        max="md"
                        render={SearchPage.renderSubscribeJobsModalButton}
                      />
                    </Col>
                    <Col xs={12} lg={0}>
                      <ResponsiveView
                        max="md"
                        render={this.renderAggregationsDrawer}
                      />
                    </Col>
                    <Col className="tr" span={12}>
                      <SortByContainer namespace={JOBS_NS} />
                    </Col>
                  </Row>
                  <Row>
                    <Col span={24}>
                      <ResultsContainer
                        namespace={JOBS_NS}
                        renderItem={SearchPage.renderJobResultItem}
                      />
                      <PaginationContainer namespace={JOBS_NS} />
                    </Col>
                  </Row>
                </LoadingOrChildren>
              </EmptyOrChildren>
            </Col>
          </Row>
        </div>
      </>
    );
  }
}

SearchPage.propTypes = {
  loading: PropTypes.bool.isRequired,
  loadingAggregations: PropTypes.bool.isRequired,
};

const stateToProps = (state) => ({
  isSuperUserLoggedIn: isSuperUser(state.user.getIn(['data', 'roles'])),
  loading: state.search.getIn(['namespaces', JOBS_NS, 'loading']),
  loadingAggregations: state.search.getIn([
    'namespaces',
    JOBS_NS,
    'loadingAggregations',
  ]),
  results: state.search.getIn(['namespaces', JOBS_NS, 'results']),
  numberOfResults: state.search.getIn(['namespaces', JOBS_NS, 'total']),
});

export default connect(stateToProps)(SearchPage);
