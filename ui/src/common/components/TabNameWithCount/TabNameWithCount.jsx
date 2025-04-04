import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { LoadingOutlined } from '@ant-design/icons';

import EventTracker from '../EventTracker';
import FormattedNumber from '../FormattedNumber';

class TabNameWithCount extends Component {
  render() {
    const { name, loading, count, page } = this.props;
    return (
      <EventTracker
        eventCategory={page}
        eventAction="Tab selection"
        eventId={`${name} tab`}
      >
        <span>
          <span>{name}</span>
          <span className="ml1">
            {loading ? (
              <span data-testid="loading">
                <LoadingOutlined className="ml1" spin />
              </span>
            ) : (
              count != null && (
                <span>
                  (<FormattedNumber>{count}</FormattedNumber>)
                </span>
              )
            )}
          </span>
        </span>
      </EventTracker>
    );
  }
}

TabNameWithCount.propTypes = {
  name: PropTypes.string.isRequired,
  loading: PropTypes.bool,
  count: PropTypes.number,
};

TabNameWithCount.defaultProps = {
  count: null,
  loading: false,
};

export default TabNameWithCount;
