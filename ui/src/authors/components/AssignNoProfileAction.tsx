import React from 'react';
import { FileDoneOutlined } from '@ant-design/icons';
import { Button, Tooltip } from 'antd';

import DropdownMenu from '../../common/components/DropdownMenu';
import IconText from '../../common/components/IconText';
import UserAction from '../../common/components/UserAction';

export const CLAIMING_DISABLED_INFO = (
  <p>
    There is no profile associated to your account. Please{' '}
    <a
      href="https://help.inspirehep.net/knowledge-base/contact-us"
      target="_blank"
    >
      contact us
    </a>
  </p>
);

function AssignNoProfileAction() {
  return (
    <UserAction>
      <DropdownMenu
        disabled
        title={
          <Tooltip title={CLAIMING_DISABLED_INFO}>
            <Button disabled data-test-id="btn-claiming-profile">
              <IconText text="claim" icon={<FileDoneOutlined />} />
            </Button>
          </Tooltip>
        }
      />
    </UserAction>
  );
}

export default AssignNoProfileAction;
