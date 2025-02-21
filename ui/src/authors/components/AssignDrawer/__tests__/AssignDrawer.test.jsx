import React from 'react';
import { render ,fireEvent} from '@testing-library/react';
import { Set } from 'immutable';

import { Provider } from 'react-redux';
import AssignDrawer from '../AssignDrawer';
import { getStore } from '../../../../fixtures/store';

jest.mock('react-router-dom', () => ({
  useParams: jest.fn().mockImplementation(() => ({
    id: 123,
  })),
}));

describe('AssignDrawer', () => {
  it('renders assign authors search', () => {
    const visible = true;
    const onDrawerClose = jest.fn();
    const onAssign = jest.fn();
    const selectedPapers = Set([1, 2, 3]);

    const { asFragment } = render(
      <Provider store={getStore()}>
      <AssignDrawer
        visible={visible}
        onDrawerClose={onDrawerClose}
        onAssign={onAssign}
        selectedPapers={selectedPapers}
      />
      </Provider>
    );
    expect(asFragment()).toMatchSnapshot();
  });

  it('calls onAssign on assign button click', () => {
    const visible = true;
    const onDrawerClose = jest.fn();
    const onAssign = jest.fn();
    const selectedPapers = Set([1, 2, 3]);

    const { getByTestId } = render(
      <Provider store={getStore()}>
        <AssignDrawer
          visible={visible}
          onDrawerClose={onDrawerClose}
          onAssign={onAssign}
          selectedPapers={selectedPapers}
        />
      </Provider>
    );
    expect(getByTestId('assign-button')).toBeDisabled();

    fireEvent.change(getByTestId('author-radio-group'), { target: { value: "321" } });
    expect(getByTestId('assign-button')).toBeEnabled();

    getByTestId('assign-button').simulate('click');
    expect(onAssign).toHaveBeenCalledWith({ from: 123, to: 321 });
  });
});
