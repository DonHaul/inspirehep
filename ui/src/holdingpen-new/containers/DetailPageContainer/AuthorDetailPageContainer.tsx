/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable no-underscore-dangle */
import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Row, Col, Button, Table } from 'antd';
import {
  LinkOutlined,
  EditOutlined,
  RedoOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlayCircleOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { Action, ActionCreator } from 'redux';
import { connect, RootStateOrAny } from 'react-redux';
import { Map } from 'immutable';

import './DetailPageContainer.less';
import Breadcrumbs from '../../components/Breadcrumbs';
import ContentBox from '../../../common/components/ContentBox';
import CollapsableForm from '../../../submissions/common/components/CollapsableForm';
import LoadingOrChildren from '../../../common/components/LoadingOrChildren';
import { fetchAuthor } from '../../../actions/holdingpen';

interface AuthorDetailPageContainerProps {
  dispatch: ActionCreator<Action>;
  author: Map<string, any>;
  loading: boolean;
}

const columnsInstitutions = [
  {
    title: 'Institution',
    dataIndex: 'institution',
  },
  {
    title: 'Start date',
    dataIndex: 'start_date',
    render: (start: string) => (!start ? '-' : start),
  },
  {
    title: 'End date',
    dataIndex: 'end_date',
    render: (end: string) => (!end ? 'Present' : end),
  },
  {
    title: 'Rank',
    dataIndex: 'rank',
    render: (rank: string) => (!rank ? '-' : rank),
  },
  {
    title: 'Current',
    dataIndex: 'current',
    render: (current: boolean) =>
      current ? (
        <CheckCircleOutlined style={{ color: 'green' }} />
      ) : (
        <CloseCircleOutlined style={{ color: 'red' }} />
      ),
    align: 'center' as const,
  },
];

const columnsProjects = [
  {
    title: 'Project name',
    dataIndex: 'name',
  },
  {
    title: 'Current',
    dataIndex: 'current',
    render: (current: boolean) =>
      current ? (
        <CheckCircleOutlined style={{ color: 'green' }} />
      ) : (
        <CloseCircleOutlined style={{ color: 'red' }} />
      ),
    align: 'center' as const,
  },
  {
    title: 'Start date',
    dataIndex: 'start_date',
    render: (start: string) => (!start ? '-' : start),
  },
  {
    title: 'End date',
    dataIndex: 'end_date',
    render: (end: string) => (!end ? 'Present' : end),
  },
];

const columnsSubject = [
  {
    title: 'Term',
    dataIndex: 'term',
  },
  {
    title: 'Action',
    // TODO: Add action to remove term
    render: () => (
      <span className="blue b pointer">
        <CloseOutlined />
      </span>
    ),
    width: '10%',
    align: 'center' as const,
  },
];

const columnsAdvisors = [
  {
    title: 'Name',
    dataIndex: 'name',
  },
  {
    title: 'Position',
    dataIndex: 'degree_type',
    render: (deg: string) => (!deg ? '-' : deg),
  },
];

const AuthorDetailPageContainer: React.FC<AuthorDetailPageContainerProps> = ({
  dispatch,
  author,
  loading,
}) => {
  const { id } = useParams<{ id: string }>();

  useEffect(() => {
    dispatch(fetchAuthor(id));
  }, []);

  const data = author?.get('data') as Map<any, any>;

  const OPEN_SECTIONS = [
    data?.get('positions') && 'institutions',
    data?.get('project_membership') && 'projects',
    (data?.get('urls') || data?.get('ids')) && 'links',
    (data?.get('arxiv_categories') || data?.get('.advisors')) && 'other',
    author?.get('_error_msg') && 'errors',
    'delete',
  ].filter(Boolean);

  return (
    <div
      className="__DetailPageContainer__"
      data-testid="holdingpen-detail-page"
    >
      <Breadcrumbs
        title1="Search"
        href1={`${document.referrer}`}
        title2={(data?.getIn(['name', 'value']) as string) || 'Details'}
        href2={id}
      />
      <LoadingOrChildren loading={loading}>
        <Row justify="center">
          <Col xs={24} md={22} lg={21} xxl={18}>
            {author?.get('status') && (
              <Row className="mv3" justify="center" gutter={35}>
                <Col xs={24}>
                  <div
                    className={`bg-${author?.get('status')?.toLowerCase()} ${
                      author?.get('status') === 'error' ? 'white' : ''
                    } w-100`}
                  >
                    <p className="b f3 tc pv2">
                      {author?.get('status').toUpperCase()}
                      {author?.get('status') !== 'completed'
                        ? ` on: "${
                            author?.get('_message') ||
                            author?.get('_last_task_name')
                          }"`
                        : ''}
                    </p>
                  </div>
                </Col>
              </Row>
            )}
            <Row className="mv3" justify="center" gutter={35}>
              <Col xs={24} lg={16}>
                <ContentBox fullHeight={false} className="md-pb3 mb3">
                  <h2>{data?.getIn(['name', 'value'])}</h2>
                  {data?.getIn(['name', 'preferred_name']) && (
                    <p>
                      <b>Preferred name:</b>{' '}
                      {data?.getIn(['name', 'preferred_name'])}
                    </p>
                  )}
                  {data?.get('status') && (
                    <p>
                      <b>Status:</b> {data?.get('status')}
                    </p>
                  )}
                  {data?.getIn(['acquisition_source', 'orcid']) && (
                    <p className="mb0">
                      <b>ORCID:</b>{' '}
                      <a
                        href={`https://orcid.org/my-orcid?orcid=${data?.getIn([
                          'acquisition_source',
                          'orcid',
                        ])}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {data?.getIn(['acquisition_source', 'orcid'])}
                      </a>
                    </p>
                  )}
                </ContentBox>
                <CollapsableForm openSections={OPEN_SECTIONS}>
                  <CollapsableForm.Section
                    header="Institution history"
                    key="institutions"
                  >
                    <Table
                      columns={columnsInstitutions}
                      dataSource={data?.get('positions')?.toJS()}
                      pagination={false}
                      size="small"
                      rowKey={(record) =>
                        `${record?.institution}+${Math.random()}`
                      }
                    />
                  </CollapsableForm.Section>
                  <CollapsableForm.Section
                    header="Project membership history"
                    key="projects"
                  >
                    <Table
                      columns={columnsProjects}
                      dataSource={data?.get('project_membership')?.toJS()}
                      pagination={false}
                      size="small"
                      rowKey={(record) => `${record?.name}+${Math.random()}`}
                    />
                  </CollapsableForm.Section>
                  {data?.get('urls') && (
                    <CollapsableForm.Section header="Links" key="links">
                      {data?.get('ids')?.map((link: Map<string, any>) => (
                        <p key={link?.get('value')}>
                          <LinkOutlined />
                          {link?.get('schema') && (
                            <b className="dib ml1 ttc">
                              {link?.get('schema').toLowerCase()}:
                            </b>
                          )}{' '}
                          <a
                            href={
                              link?.get('schema') === 'LINKEDIN'
                                ? `https://www.linkedin.com/in/${link?.get(
                                    'value'
                                  )}`
                                : `https://orcid.org/my-orcid?orcid=${link?.get(
                                    'value'
                                  )}`
                            }
                          >
                            {link?.get('value')}
                          </a>
                        </p>
                      ))}
                      {data?.get('urls')?.map((link: Map<string, any>) => (
                        <p key={link?.get('value')}>
                          <LinkOutlined />
                          {link?.get('description') && (
                            <b className="dib ml1 ttc">
                              {link?.get('description')}:
                            </b>
                          )}{' '}
                          <a href={link?.get('value')}>{link?.get('value')}</a>
                        </p>
                      ))}
                    </CollapsableForm.Section>
                  )}
                  <CollapsableForm.Section header="Other" key="other">
                    <Row justify="space-between" gutter={12}>
                      <Col xl={12}>
                        <h3 className="mb3">Subject areas</h3>
                        <Table
                          columns={columnsSubject}
                          dataSource={data
                            ?.get('arxiv_categories')
                            ?.toJS()
                            ?.map((term: string) => ({ term }))}
                          pagination={false}
                          size="small"
                          rowKey={(record) =>
                            `${record?.term}+${Math.random()}`
                          }
                        />
                      </Col>
                      <Col xl={12}>
                        <h3 className="mb3">Advisors</h3>
                        <Table
                          columns={columnsAdvisors}
                          dataSource={data?.get('advisors')?.toJS()}
                          pagination={false}
                          size="small"
                          rowKey={(record) =>
                            `${record?.name}+${Math.random()}`
                          }
                        />
                      </Col>
                    </Row>
                  </CollapsableForm.Section>
                  {author?.get('_error_msg') && (
                    <CollapsableForm.Section header="Errors" key="errors">
                      <div className="bg-waiting error-code">
                        {author?.get('_error_msg')}
                      </div>
                    </CollapsableForm.Section>
                  )}
                  <CollapsableForm.Section header="Danger area" key="delete">
                    <Button className="font-white bg-error">Delete</Button>
                  </CollapsableForm.Section>
                </CollapsableForm>
              </Col>
              <Col xs={24} lg={8}>
                <ContentBox
                  className="mb3"
                  fullHeight={false}
                  subTitle="Decision"
                >
                  <div className="w-100 flex flex-column items-center">
                    <Button type="primary" className="font-white w-75 mb2">
                      Review submission
                    </Button>
                    <Button className="font-white bg-completed w-75 mb2">
                      Accept
                    </Button>
                    <Button className="font-white bg-halted w-75 mb2">
                      Accept + Curation
                    </Button>
                    <Button className="font-white bg-error w-75 mb2">
                      Reject
                    </Button>
                  </div>
                </ContentBox>
                <ContentBox
                  className="mb3"
                  fullHeight={false}
                  subTitle="Submission"
                >
                  Submitted by{' '}
                  <i>{data?.getIn(['acquisition_source', 'email'])}</i> on{' '}
                  <b>
                    {new Date(
                      data?.getIn(['acquisition_source', 'datetime']) as Date
                    ).toLocaleDateString()}
                  </b>
                  .
                </ContentBox>
                {/* TODO: find out how notes are stored in workflow */}
                {data?.get('notes') && (
                  <ContentBox
                    className="mb3"
                    fullHeight={false}
                    subTitle="Notes"
                  >
                    <i>&quot;Thank you for reviewing my submission&quot;</i>
                  </ContentBox>
                )}
                <ContentBox
                  className="mb3"
                  fullHeight={false}
                  subTitle="SNow information"
                >
                  {author?.get('ticket_id') && (
                    <a
                      href={author?.get('ticket_url')}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      See related ticket #{author?.get('ticket_id')}
                    </a>
                  )}
                </ContentBox>
                <ContentBox fullHeight={false} subTitle="Actions">
                  <div className="flex flex-column items-center">
                    <Button className="mb2 w-75">
                      <SyncOutlined />
                      Restart workflow
                    </Button>
                    <Button className="mb2 w-75">
                      <RedoOutlined />
                      Restart current step
                    </Button>
                    <Button className="mb2 w-75" type="primary">
                      <a
                        href={`/editor/holdingpen/${data?.get('id')}`}
                        target="_blank"
                        rel="noreferrer noopener"
                      >
                        <EditOutlined />
                        {'  '}
                        Open in Editor
                      </a>
                    </Button>
                    <Button className="w-75">
                      <PlayCircleOutlined />
                      Skip to next step
                    </Button>
                  </div>
                </ContentBox>
              </Col>
            </Row>
          </Col>
        </Row>
      </LoadingOrChildren>
    </div>
  );
};

const stateToProps = (state: RootStateOrAny) => ({
  author: state.holdingpen.get('author'),
  loading: state.holdingpen.get('loading'),
});

export default connect(stateToProps)(AuthorDetailPageContainer);