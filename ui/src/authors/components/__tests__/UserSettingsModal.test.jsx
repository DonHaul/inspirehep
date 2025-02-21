import React from 'react';
import { render } from '@testing-library/react';
import { Provider } from 'react-redux';

import UserSettingsModal from '../UserSettingsModal';
import { getStore } from '../../../fixtures/store';

describe('UserSettingsModal', () => {
  it('renders with props', () => {
    const { asFragment } = render(
      <Provider store={getStore()}>
        <UserSettingsModal visible onCancel={jest.fn()} />
      </Provider>
    );
    expect(asFragment()).toMatchSnapshot();
  });

  it('calls onCancel on modal cancel', () => {
    const onCancel = jest.fn();
    const { getByLabelText } = render(
      <Provider store={getStore()}>
        <UserSettingsModal visible onCancel={onCancel} />
      </Provider>
    );

    getByLabelText('Close').click();
    expect(onCancel).toHaveBeenCalled();
  });
});
