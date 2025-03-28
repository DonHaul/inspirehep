import React, { Component } from 'react';
import { MessageOutlined } from '@ant-design/icons';
import { Modal, Button, Rate, Input, Alert } from 'antd';

import './UserFeedback.less';
import { trackEvent, checkIsTrackerBlocked } from '../../../tracker';
import LinkWithTargetBlank from '../LinkWithTargetBlank';
import ResponsiveView from '../ResponsiveView';
import ModalSuccessResult from '../ModalSuccessResult';
import { SURVEY_LINK } from '../../constants';

const RATE_DESCRIPTIONS = [
  'poor',
  'below average',
  'average',
  'good',
  'excellent',
];

class UserFeedback extends Component {
  static renderThankYou() {
    return (
      <ModalSuccessResult>
        <div>Thank you for your response.</div>
        <div>
          For further feedback, please{' '}
          <LinkWithTargetBlank href={SURVEY_LINK}>
            take our survey
          </LinkWithTargetBlank>
          .
        </div>
        <div>It takes around 5 minutes to complete.</div>
      </ModalSuccessResult>
    );
  }

  constructor(props) {
    super(props);

    this.onFeedbackClick = this.onFeedbackClick.bind(this);
    this.onModalCancel = this.onModalCancel.bind(this);
    this.onFeedbackSubmit = this.onFeedbackSubmit.bind(this);
    this.onCommentChange = this.onCommentChange.bind(this);
    this.onRateChange = this.onRateChange.bind(this);
    this.afterModalClose = this.afterModalClose.bind(this);

    this.state = {
      isModalVisible: false,
      isFeedbackButtonVisible: true,
      feedbackSubmitted: false,
      rateValue: 0,
    };
  }

  onFeedbackClick() {
    this.setState({
      isModalVisible: true,
      isFeedbackButtonVisible: false,
    });
  }

  onModalCancel() {
    this.setState({
      isModalVisible: false,
      isFeedbackButtonVisible: true,
    });
  }

  onFeedbackSubmit() {
    const { rateValue, commentValue } = this.state;
    trackEvent(
      'Feedback modal',
      'Feedback submission',
      `Feedback comment: ${commentValue}`,
      rateValue
    );
    this.setState({
      rateValue: 0,
      commentValue: null,
      feedbackSubmitted: true,
    });
  }

  onCommentChange(event) {
    const { value } = event.target;
    this.setState({ commentValue: value });
  }

  onRateChange(rateValue) {
    this.setState({ rateValue });
  }

  afterModalClose() {
    this.setState({
      feedbackSubmitted: false,
    });
  }

  renderFeedbackForm() {
    const { rateValue, commentValue } = this.state;
    const isTrackerBlocked = checkIsTrackerBlocked();
    return (
      <>
        {isTrackerBlocked && (
          <div className="mb4">
            <Alert
              type="warning"
              showIcon
              message="AdBlock detected"
              description={
                <>
                  <p>
                    To send us your feedback, please disable your adblocker or
                    DoNotTrack and refresh the page.
                  </p>
                  <p>
                    Alternatively, you could send us your feedback using the{' '}
                    <LinkWithTargetBlank href={SURVEY_LINK}>
                      feedback form
                    </LinkWithTargetBlank>{' '}
                    or
                    <a
                      href="https://help.inspirehep.net/knowledge-base/contact-us"
                      target="_blank"
                    >
                      contact us
                    </a>
                    .
                  </p>
                </>
              }
            />
          </div>
        )}
        <div className="mb4">
          <div className="mb1">What is your opinion of the new INSPIRE?</div>
          <div>
            <Rate
              disabled={isTrackerBlocked}
              value={rateValue}
              onChange={this.onRateChange}
            />
            <span className="ant-rate-text">
              {RATE_DESCRIPTIONS[rateValue - 1]}
            </span>
          </div>
        </div>
        <div>
          <div className="mb1">Would you like to add a comment?</div>
          <div>
            <Input.TextArea
              disabled={isTrackerBlocked}
              placeholder="Please give your feedback here"
              rows={5}
              value={commentValue}
              onChange={this.onCommentChange}
            />
          </div>
        </div>
      </>
    );
  }

  render() {
    const { isModalVisible, isFeedbackButtonVisible, feedbackSubmitted } =
      this.state;
    const isTrackerBlocked = checkIsTrackerBlocked();
    return (
      <div className="__UserFeedback__">
        {isFeedbackButtonVisible && (
          <Button
            data-test-id="sticky"
            className="feedback-button"
            type="primary"
            size="large"
            icon={<MessageOutlined />}
            onClick={this.onFeedbackClick}
          >
            <ResponsiveView min="sm" render={() => <span>Feedback</span>} />
          </Button>
        )}
        <Modal
          data-testid="user-feedback"
          title="Your Feedback"
          open={isModalVisible}
          onOk={this.onFeedbackSubmit}
          okText="Submit"
          okButtonProps={{ disabled: isTrackerBlocked }}
          onCancel={this.onModalCancel}
          footer={feedbackSubmitted ? null : undefined} // undefined enables default footer with OK btn
          afterClose={this.afterModalClose}
        >
          {feedbackSubmitted
            ? UserFeedback.renderThankYou()
            : this.renderFeedbackForm()}
        </Modal>
      </div>
    );
  }
}

export default UserFeedback;
