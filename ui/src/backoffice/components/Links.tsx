import React from 'react';
import { Map } from 'immutable';
import { LinkOutlined, LinkedinOutlined, XOutlined } from '@ant-design/icons';

import orcidLogo from '../../common/assets/orcid.svg';

interface LinksProps {
  urls: Map<string, any>;
  ids: Map<string, any>;
}

function getLinkData(schema: string, value: string) {
  switch (schema) {
    case 'LINKEDIN':
      return {
        href: `https://www.linkedin.com/in/${value}`,
        icon: <LinkedinOutlined className="mr1" />,
      };
    case 'TWITTER':
      return {
        href: `https://x.com/${value}`,
        icon: <XOutlined className="mr1" />,
      };
    case 'BLUESKY':
      return {
        href: `https://bsky.app/profile/${value}`,
        icon: <XOutlined className="mr1" />,
      };
    case 'MASTODON': {
      const [user, host] = value.split('@');
      return {
        href: `https://${host}/@${user}`,
        icon: <XOutlined className="mr1" />,
      };
    }
    case 'ORCID':
      return {
        href: `https://orcid.org/my-orcid?orcid=${value}`,
        icon: (
          <img
            src={orcidLogo}
            alt="ORCID"
            width={16}
            height={16}
            className="mr1"
          />
        ),
      };
    default:
      return {
        href: value,
        icon: <LinkOutlined className="mr1" />,
      };
  }
}

export const Ids: React.FC<{ ids: Map<string, any>; noIcon?: boolean }> = ({
  ids,
  noIcon = false,
}) => (
  <>
    {ids?.map((link: Map<string, any>) => (
      <p key={link?.get('value')} className={noIcon ? 'mb0' : ''}>
        {!noIcon && getLinkData(link?.get('schema'), link?.get('value'))?.icon}
        {link?.get('schema') && (
          <b className="dib ttc">{link?.get('schema').toLowerCase()}:</b>
        )}{' '}
        <a
          href={getLinkData(link?.get('schema'), link?.get('value'))?.href}
          target="_blank"
        >
          {link?.get('value')}
        </a>
      </p>
    ))}
  </>
);

export const Urls: React.FC<{ urls: Map<string, any> }> = ({ urls }) => (
  <>
    {urls?.map((link: Map<string, any>) => (
      <p key={link?.get('value')}>
        {getLinkData(link?.get('schema'), link?.get('value'))?.icon}
        {link?.get('description') && (
          <b className="dib ml1 ttc">{link?.get('description')}:</b>
        )}{' '}
        <a href={link?.get('value')} target="_blank">
          {link?.get('value')}
        </a>
      </p>
    ))}
  </>
);

const Links: React.FC<LinksProps> = ({ urls, ids }) => {
  return (
    <>
      <Ids ids={ids} />
      <Urls urls={urls} />
    </>
  );
};

export default Links;
